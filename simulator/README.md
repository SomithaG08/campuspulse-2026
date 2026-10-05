# Simulator

Pretends to be the campus IoT devices. Zero dependencies — standard library only.

```bash
export CAMPUSPULSE_API=https://xxxx.execute-api.eu-west-3.amazonaws.com
export CAMPUSPULSE_USER=device@campuspulse.local
export CAMPUSPULSE_PASSWORD='...'

python simulator.py --dry-run -n 10      # print only, no AWS, no cost
python simulator.py -n 100               # send 100 and stop
python simulator.py --interval 5         # one every 5s until Ctrl-C
python simulator.py --force-alert -n 3   # guaranteed critical, for the demo
```

Credentials come from the environment, never the command line — an argument lands in your shell history and the process list.

Imports `backend/src/common/campus_config.py` and `rules.py` so the simulator and the server can never disagree about the campus.

Tests: `python -m pytest simulator/tests -q` · Explanation: `docs/learning/14-simulator-explained.md`
