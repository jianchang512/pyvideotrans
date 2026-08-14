{
  description = "pyVideoTrans WebUI Flake";

  inputs = {
    nixpkgs.url = "github:NixOS/nixpkgs/nixos-unstable";
    flake-utils.url = "github:numtide/flake-utils";
  };

  outputs = { self, nixpkgs, flake-utils }:
    flake-utils.lib.eachDefaultSystem (system:
      let
        pkgs = import nixpkgs {
          inherit system;
          config.allowUnfree = true;
        };

        # Shared libraries required by Python wheels (PyTorch, PySide6, OpenCV, CTranslate2, etc.)
        runtimeLibs = with pkgs; [
          stdenv.cc.cc.lib
          zlib
          glib
          libGL
          libGLU
          libglvnd
          libx11
          libxext
          libxrender
          libsm
          libice
          libxcb
          libxkbfile
          libxkbcommon
          dbus
          alsa-lib
          libpulseaudio
          libsndfile
          rubberband
          fontconfig
          openssl
        ];

        libPath = pkgs.lib.makeLibraryPath runtimeLibs;

        envVars = ''
          export LD_LIBRARY_PATH="${libPath}:$LD_LIBRARY_PATH"
          export FONTCONFIG_PATH="${pkgs.fontconfig.out}/etc/fonts"
          export PYTHONUNBUFFERED=1
          export UV_PYTHON_DOWNLOADS="never"
          export USE_CUDA="''${USE_CUDA:-false}"
        '';

        checkDependencies = ''
          # 1. Check Python 3.10 (strict local only, no downloads allowed)
          if ! uv python find 3.10 >/dev/null 2>&1; then
            echo "ERROR: Python 3.10 is required by pyproject.toml but was not found locally." >&2
            echo "       UV_PYTHON_DOWNLOADS is set to 'never', so uv will not auto-download it." >&2
            return 1 2>/dev/null || exit 1
          fi

          # 2. Check FFmpeg (minimum version 6.0)
          if ! command -v ffmpeg >/dev/null 2>&1; then
            echo "ERROR: ffmpeg is not installed or not found in PATH." >&2
            return 1 2>/dev/null || exit 1
          fi
          FFMPEG_VER=$(ffmpeg -version 2>&1 | head -n1 | sed -nE 's/^[^0-9]*([0-9]+(\.[0-9]+)*).*/\1/p')
          MIN_FFMPEG="6.0"
          if [ -n "$FFMPEG_VER" ] && [ "$(printf '%s\n%s' "$MIN_FFMPEG" "$FFMPEG_VER" | sort -V | head -n1)" != "$MIN_FFMPEG" ]; then
            echo "ERROR: ffmpeg version $FFMPEG_VER is lower than required minimum $MIN_FFMPEG." >&2
            return 1 2>/dev/null || exit 1
          fi

          # 3. Check Rubberband (minimum version 3.0.0)
          if ! command -v rubberband >/dev/null 2>&1; then
            echo "ERROR: rubberband is not installed or not found in PATH." >&2
            return 1 2>/dev/null || exit 1
          fi
          RUBBERBAND_VER=$(rubberband --version 2>&1 | head -n1 | sed -nE 's/^[^0-9]*([0-9]+(\.[0-9]+)*).*/\1/p')
          MIN_RUBBERBAND="3.0.0"
          if [ -n "$RUBBERBAND_VER" ] && [ "$(printf '%s\n%s' "$MIN_RUBBERBAND" "$RUBBERBAND_VER" | sort -V | head -n1)" != "$MIN_RUBBERBAND" ]; then
            echo "ERROR: rubberband version $RUBBERBAND_VER is lower than required minimum $MIN_RUBBERBAND." >&2
            return 1 2>/dev/null || exit 1
          fi
        '';

        initVenv = ''
          if [ ! -d ".venv" ]; then
            echo ">>> Creating .venv with local Python 3.10..."
            uv venv --python 3.10 .venv
          fi
          source .venv/bin/activate
        '';

        syncDeps = ''
          if [ "''${USE_CUDA:-false}" = "true" ]; then
            echo ">>> Installing dependencies with CUDA (12.8) support..."
            uv pip install torch==2.7.1 torchaudio==2.7.1 --index-url https://download.pytorch.org/whl/cu128
            uv pip install nvidia-cublas-cu12 nvidia-cudnn-cu12
          else
            echo ">>> Installing dependencies for CPU (no CUDA/nvidia packages)..."
            # Pre-install CPU PyTorch so that 'uv pip install -r pyproject.toml' sees torch as satisfied and does not download NVIDIA CUDA wheels
            uv pip install torch==2.7.1+cpu torchaudio==2.7.1+cpu --index-url https://download.pytorch.org/whl/cpu
          fi
          uv pip install -r pyproject.toml --all-extras
        '';

        syncDepsBin = pkgs.writeShellScriptBin "sync-deps" ''
          set -e
          ${envVars}
          ${checkDependencies}
          ${initVenv}
          ${syncDeps}
        '';

        runWebui = pkgs.writeShellScriptBin "pyvideotrans-webui" ''
          set -e
          ${envVars}
          ${checkDependencies}
          ${initVenv}
          ${syncDeps}
          exec python webui.py "$@"
        '';

      in {
        devShells.default = pkgs.mkShell {
          packages = [ pkgs.pkg-config syncDepsBin ] ++ runtimeLibs;

          shellHook = ''
            ${envVars}
            ${checkDependencies}
            ${initVenv}

            echo -e "\033[1;32m✨ 🎬 pyVideoTrans Nix Environment Ready! 🚀\033[0m"
            if [ "''${USE_CUDA:-false}" = "true" ]; then
              echo -e "⚡ \033[1;33mMode:\033[0m \033[1;35mGPU / CUDA enabled 🟢\033[0m"
            else
              echo -e "💻 \033[1;33mMode:\033[0m \033[1;36mCPU (No CUDA/NVIDIA wheels)\033[0m \033[90m(set 'export USE_CUDA=true' for GPU)\033[0m"
            fi
            echo -e "📦 \033[1;34mSync Deps:\033[0m  \033[1m\033[4;32msync-deps\033[0m"
            echo -e "▶️ \033[1;34mStart WebUI:\033[0m \033[1m\033[4;32mpython webui.py\033[0m"
          '';
        };

        apps.default = {
          type = "app";
          program = "${runWebui}/bin/pyvideotrans-webui";
        };
      }
    );
}
