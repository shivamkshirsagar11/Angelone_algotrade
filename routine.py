import os


def start_routine(startingMsg="Starting trading", script_names=[]):
    os.system(f"echo {startingMsg}...")
    for script in script_names:
        os.system(f"echo Executing {script}.py")
        os.system(f"python {script}.py")

start_routine("Starting Backtesting", script_names=["utility", "backtest"])