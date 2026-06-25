# Arena Shooter — Panda3D

A top-down arena shooter built with **Python + Panda3D**, developed as a game development portfolio project.

## Gameplay

Survive endless waves of enemies in a closed arena. Aim with the mouse, shoot with left-click, and move with WASD. Each wave spawns more enemies than the last — how long can you last?

### Features
- Top-down perspective with real-time mouse aiming
- Collision detection using Panda3D's built-in traversal system
- Progressive wave difficulty (each wave adds 3 more enemies)
- Health system with 5 hit points and visual HUD feedback
- Score tracking across waves
- Game over and wave-clear states with restart support

## Controls

| Key / Button | Action |
|---|---|
| W A S D | Move player |
| Left Click | Shoot toward cursor |
| R | Restart game |
| Escape | Quit |

## Screenshots

> Run the game locally to see it in action — see instructions below.

## Tech Stack

- **Language:** Python 3.10+
- **Engine:** Panda3D 1.10+
- **Rendering:** Real-time 3D with orthographic top-down camera
- **Physics / Collision:** Panda3D CollisionTraverser + CollisionHandlerQueue
- **UI:** OnscreenText HUD (score, health, wave counter)

## Project Structure

```
panda3d-arena-shooter/
├── main.py           # Game entry point — all game logic
├── requirements.txt  # Python dependencies
└── README.md
```

## How to Run

**Prerequisites:** Python 3.10 or higher

```bash
# 1. Clone the repo
git clone https://github.com/jesugeorge/panda3d-arena-shooter.git
cd panda3d-arena-shooter

# 2. Install dependency
pip install -r requirements.txt

# 3. Launch the game
python main.py
```

## Design Decisions

- **Pure procedural rendering** — all game objects are built using Panda3D's `CardMaker` API with no external assets, keeping the project fully self-contained and portable.
- **Collision layers via BitMask32** — separate bitmasks for player, bullet, and enemy collisions prevent false positive detections between same-type entities.
- **Frame-rate independent movement** — all movement is multiplied by `dt` (delta time), ensuring consistent gameplay across different hardware.
- **Wave-pause system** — a 2.5-second pause between waves gives clear feedback and prevents immediate respawn overwhelming.

## Author

**Jesudas George**
- GitHub: [github.com/jesugeorge](https://github.com/jesugeorge)
- LinkedIn: [linkedin.com/in/jesudas-george](https://linkedin.com/in/jesudas-george)
