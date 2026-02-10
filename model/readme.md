# running and testing the model

1. Ensure that ollama is installed and configured
2. `ollama pull phi4-mini`
3. create a virtual environment
   `python3 -m venv .venv` (Linux)
   `python -m venv .venv` (Windows)
4. install requirements
   `pip install -r requirements.txt`
5. run single query
   `python main.py <query>`
6. run interactive mode
   `python main.py`

## tools and functionalities currrently implemented with the parsing engine
- get_system_metrics
- get_time