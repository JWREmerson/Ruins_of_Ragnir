# Ruins of Ragnir

**A digital implementation of the Ruins of Ragnir tabletop game using Python and Pygame.**

## Repository
Clone or download the source from GitHub:
```
git clone https://github.com/<your-username>/ruins-of-ragnir.git
cd ruins-of-ragnir
```

## Prerequisites
- Python 3.8 or higher
- pip
- A terminal (e.g., JupyterHub terminal or local shell)

## Installation
Install required Python packages:

pip install -r requirements.txt

## Project Structure

├── config.py
├── server.py
├── client.py
├── requirements.txt
├── resources/
│   ├── GateCards.json
│   ├── HeroCards.json
│   ├── RuinCards.json
│   ├── MinionCards.json
│   ├── GearCards.json
│   ├── SpellCards.json
│   ├── RelicCards.json
│   ├── GlyphCards.json
│   └── ...
├── network/
│   ├── server_core.py
│   ├── client_core.py
│   └── protocol.py
├── game/
│   ├── init.py
│   ├── state.py
│   ├── phases.py
│   └── ...
├── ui/
│   ├── deck_selection.py
│   └── display.py
├── models.py
├── utils.py
├── loader.py
└── README.md

## Running the Game
1. **Start the Server**  
   Open a terminal in your JupyterHub (or local shell) and run:
   
   python server.py


2. **Launch Two Clients**  
   Open two separate terminals for the clients and run in each:

   python client.py

   Each client will prompt for deck selection via a GUI. Click two separate decks to prevent crashing.

3. **Gameplay**  
   - The server coordinates the **Explore Phase** until a path is connected.  
   - 
   - Windows can be closed to exit. Closing the first causes it to seize until you hit enter in the terminal, which wil lcrash both. 
   
## JupyterHub Notes
- Use the built-in terminal to run server and clients.  
- Ensure ports (default `54321`) are open within your environment.  
- No browser-based UI—clients use Pygame windows.
```