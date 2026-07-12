"""Runtime patches that make vLLM serve the Confucius4-TTS T2S model.

Importing this module has two side effects, both required before an engine is
created:

1. Registers the custom ``Text2SemanticVLLM`` architecture in vLLM's model
   registry so it can be loaded by name.
2. Monkeypatches ``GPUModelRunner._prepare_inputs`` so that, for this model,
   position ids are shifted to be relative to the start of the *semantic*
   sequence (excluding the speaker/text/BOS prefix). The T2S positional
   embeddings are trained on that convention, so without this correction the
   generated audio would be wrong.
"""

from vllm import ModelRegistry
from confuciustts.llm.llm_vllm import Text2SemanticVLLM

ModelRegistry.register_model("Text2SemanticVLLM", Text2SemanticVLLM)
print("Registered Text2SemanticVLLM into vLLM ModelRegistry")


def register_models():
    # Kept as an explicit no-op entry point: importing this module already does
    # the registration, but callers can reference this to force the import.
    pass

import numpy as np
import torch
from vllm.v1.worker.gpu_model_runner import GPUModelRunner
from vllm.v1.core.sched.output import SchedulerOutput
from vllm.v1.spec_decode.metadata import SpecDecodeMetadata


def _prepare_inputs(
    self,
    scheduler_output: "SchedulerOutput",
    num_scheduled_tokens: np.ndarray,
) -> tuple[torch.Tensor, SpecDecodeMetadata | None]:
    """Patched copy of ``GPUModelRunner._prepare_inputs``.

    Identical to vLLM's implementation except for the Text2SemanticVLLM-specific
    position correction below (marked with a comment): for that model, every
    request's positions are shifted back by the prefix length so the semantic
    sequence starts at position 0.
    """
    total_num_scheduled_tokens = scheduler_output.total_num_scheduled_tokens
    assert total_num_scheduled_tokens > 0
    num_reqs = self.input_batch.num_reqs
    assert num_reqs > 0

    self.input_batch.block_table.commit_block_table(num_reqs)

    req_indices = np.repeat(self.arange_np[:num_reqs], num_scheduled_tokens)
    cu_num_tokens, arange = self._get_cumsum_and_arange(num_scheduled_tokens)

    positions_np = self.positions.np[:total_num_scheduled_tokens]
    np.add(
        self.input_batch.num_computed_tokens_cpu[req_indices],
        arange,
        out=positions_np,
    )

    if self.uses_mrope:
        self._calc_mrope_positions(scheduler_output)
    if self.uses_xdrope_dim > 0:
        self._calc_xdrope_positions(scheduler_output)

    token_indices = (
        positions_np + req_indices * self.input_batch.token_ids_cpu.shape[1]
    )
    token_indices_tensor = torch.from_numpy(token_indices)
    torch.index_select(
        self.input_batch.token_ids_cpu_tensor.flatten(),
        0,
        token_indices_tensor,
        out=self.input_ids.cpu[:total_num_scheduled_tokens],
    )

    if self.enable_prompt_embeds:
        is_token_ids = self.input_batch.is_token_ids_tensor.flatten()
        torch.index_select(
            is_token_ids,
            0,
            token_indices_tensor,
            out=self.is_token_ids.cpu[:total_num_scheduled_tokens],
        )

    if self.input_batch.req_prompt_embeds:
        output_idx = 0
        for req_idx in range(num_reqs):
            num_sched = num_scheduled_tokens[req_idx]
            if req_idx not in self.input_batch.req_prompt_embeds:
                output_idx += num_sched
                continue
            if num_sched <= 0:
                output_idx += num_sched
                continue
            req_embeds = self.input_batch.req_prompt_embeds[req_idx]
            start_pos = self.input_batch.num_computed_tokens_cpu[req_idx]
            if start_pos >= req_embeds.shape[0]:
                output_idx += num_sched
                continue
            end_pos = start_pos + num_sched
            actual_end = min(end_pos, req_embeds.shape[0])
            actual_num_sched = actual_end - start_pos
            if actual_num_sched > 0:
                self.inputs_embeds.cpu[
                    output_idx: output_idx + actual_num_sched
                ].copy_(req_embeds[start_pos:actual_end])
            output_idx += num_sched

    self.input_batch.block_table.compute_slot_mapping(req_indices, positions_np)
    self.input_batch.block_table.commit_slot_mapping(total_num_scheduled_tokens)

    # --- Text2SemanticVLLM position correction ---
    # The prompt is [prefix embeds ... , BOS]; the semantic positional embeddings
    # expect BOS at position 0 and generated tokens at 1, 2, ... Subtract
    # (prompt_len - 1) from every position so the prefix lands on negative
    # indices (clamped to 0 in the model) and the semantic run starts at 0.
    model = self.get_model()
    if isinstance(model, Text2SemanticVLLM):
        prompt_tokens_offset = []
        for req_id in self.input_batch.req_ids[:num_reqs]:
            prompt_tokens_offset.append(
                -(len(self.requests[req_id].prompt_token_ids) - 1)
            )
        np.add(
            np.array(prompt_tokens_offset, dtype=np.int64)[req_indices],
            positions_np,
            out=positions_np,
        )

    self.query_start_loc.np[0] = 0
    self.query_start_loc.np[1: num_reqs + 1] = cu_num_tokens
    self.query_start_loc.np[num_reqs + 1:].fill(cu_num_tokens[-1])
    self.query_start_loc.copy_to_gpu()
    query_start_loc = self.query_start_loc.gpu[: num_reqs + 1]

    self.seq_lens.np[:num_reqs] = (
        self.input_batch.num_computed_tokens_cpu[:num_reqs] + num_scheduled_tokens
    )
    self.seq_lens.np[num_reqs:].fill(0)
    self.seq_lens.copy_to_gpu()

    num_tokens = [self.requests[r].num_tokens for r in self.input_batch.req_ids[:num_reqs]]
    num_tokens_np = np.array(num_tokens, dtype=np.int32)

    self.discard_request_mask.np[:num_reqs] = (
        self.seq_lens.np[:num_reqs] < num_tokens_np
    )
    self.discard_request_mask.copy_to_gpu(num_reqs)

    self._prepare_input_ids(
        scheduler_output,
        total_num_scheduled_tokens,
        cu_num_tokens,
    )

    if self.uses_mrope:
        self.mrope_positions.gpu[:, :total_num_scheduled_tokens].copy_(
            self.mrope_positions.cpu[:, :total_num_scheduled_tokens],
            non_blocking=True,
        )
    elif self.uses_xdrope_dim > 0:
        self.xdrope_positions.gpu[:, :total_num_scheduled_tokens].copy_(
            self.xdrope_positions.cpu[:, :total_num_scheduled_tokens],
            non_blocking=True,
        )
    else:
        self.positions.copy_to_gpu(total_num_scheduled_tokens)

    use_spec_decode = len(scheduler_output.scheduled_spec_decode_tokens) > 0
    if not use_spec_decode:
        logits_indices = query_start_loc[1:] - 1
        spec_decode_metadata = None
        num_sampled_tokens = np.ones(num_reqs, dtype=np.int32)
    else:
        num_draft_tokens = np.zeros(num_reqs, dtype=np.int32)
        num_decode_draft_tokens = np.full(num_reqs, -1, dtype=np.int32)
        for req_id, draft_token_ids in (
            scheduler_output.scheduled_spec_decode_tokens.items()
        ):
            req_idx = self.input_batch.req_id_to_index[req_id]
            num_draft_tokens[req_idx] = len(draft_token_ids)
            if (
                self.input_batch.num_computed_tokens_cpu[req_idx]
                >= self.input_batch.num_prompt_tokens[req_idx]
            ):
                num_decode_draft_tokens[req_idx] = len(draft_token_ids)
        spec_decode_metadata = self._calc_spec_decode_metadata(
            num_draft_tokens, cu_num_tokens
        )
        logits_indices = spec_decode_metadata.logits_indices
        num_sampled_tokens = num_draft_tokens + 1
        self.num_decode_draft_tokens.np[:num_reqs] = num_decode_draft_tokens
        self.num_decode_draft_tokens.np[num_reqs:].fill(-1)
        self.num_decode_draft_tokens.copy_to_gpu()

    if self.lora_config:
        assert (
            np.sum(num_sampled_tokens)
            <= self.vllm_config.scheduler_config.max_num_batched_tokens
        )
        self.set_active_loras(
            self.input_batch, num_scheduled_tokens, num_sampled_tokens
        )

    return logits_indices, spec_decode_metadata


# Install the patched method in place of vLLM's original.
GPUModelRunner._prepare_inputs = _prepare_inputs
print("GPUModelRunner._prepare_inputs patched for Confucius4-TTS position correction")
