> **# Stress Tests**
> 
> These scripts were developed during the "WinError 10054" investigation to determine the limits of Archicad's C++ HTTP server.
>
> **⚠️ WARNING:** These scripts are destructive. They are designed to overwhelm the Archicad API and **will likely crash Archicad**. Do not run these on a machine with unsaved work.
>
> **Usage:**
> `python scripts/stress_concurrency.py --port 19723`
