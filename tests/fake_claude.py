"""Claude giả cho test bộ chạy việc."""
import json
import os
import sys
import time

from vpak import ghi_so

args = sys.argv[1:]
prompt = args[args.index("-p") + 1] if "-p" in args else ""
resume = args[args.index("--resume") + 1] if "--resume" in args else ""
if os.environ.get("FAKE_ENV_OUT"):
    with open(os.environ["FAKE_ENV_OUT"], "w", encoding="utf-8") as f:
        json.dump({"env": dict(os.environ), "args": args}, f, ensure_ascii=False)
time.sleep(float(os.environ.get("FAKE_SLEEP", "0")))
if os.environ.get("FAKE_FAIL") == "1":
    print("Error: Credit balance is too low", file=sys.stderr)
    sys.exit(1)
job = os.environ["VPAK_JOB_ID"]
if os.environ.get("FAKE_ASK") == "1" and not resume:
    ghi_so.main(["giao", "--task", job + ".1", "--agent", "soat-cap-2", "--desc", "Soát cấp 2"])
    ghi_so.main(["hoi", "--task", job + ".1", "--agent", "soat-cap-2", "--q", "Chấp nhận bản scan?", "--chon", "Có", "--chon", "Không"])
else:
    ghi_so.main(["giao", "--task", job + ".2", "--agent", "soat-cap-1", "--desc", "Soát cấp 1"])
    ghi_so.main(["xong", "--task", job + ".2"])
print(json.dumps({"session_id": "fake-1", "result": "ok", "resumed": resume, "usage": {"output_tokens": 10}}))
