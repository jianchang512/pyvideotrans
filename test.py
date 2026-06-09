from videotrans.task.taskcfg import SrtItem


a=SrtItem(
                line=1,
                start_time=0,
                end_time=2000,
                endraw="00:00:02,000",
                time="00:00:00,000 --> 00:00:02,000",
                text="\n"
            )
print("startraw" in a)