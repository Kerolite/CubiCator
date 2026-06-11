# CubiCator 🟧
> Rubik's Cube solving robot — INSA student project

## Team

| Role | Contributor |
|------|-------------|
| Code & Electronics | Solo |
| Mathematics (Kociemba, cube model) | × 2 |
| CAD & Mechanics | × 2 (incl. code/electronics lead) |

## How it works

1. The robot rotates the cube in front of a fixed webcam to expose all 6 faces.
2. The user clicks the 9 sticker positions once on the camera preview.
3. Colors are sampled via median RGB on each position and matched to face centers.
4. The [Kociemba algorithm](https://github.com/muodov/kociemba) computes an optimal solution.
5. The solution is sent over serial to the Arduino, which executes the move sequence via servo motors.

## Hardware

- Arduino Nano
- 8 servo motors — 4 rails (engage/disengage) + 4 claws (rotate)
- External 5V power supply for servos (**common GND with Arduino required**)
- Webcam

## Wiring

| Signal        | Arduino pin |
|---------------|-------------|
| Rail UP / DOWN | 9          |
| Rail RIGHT / LEFT | 3       |
| Claw UP       | 11          |
| Claw DOWN     | 10          |
| Claw RIGHT    | 5           |
| Claw LEFT     | 6           |

> Rails UP and DOWN share the same pin, as do RIGHT and LEFT — both sliders on an axis move together.

## Dependencies

### Python
```bash
pip install pyserial opencv-python numpy kociemba Pillow
```

### Arduino
- `Servo.h` (built-in)

## Usage

1. Flash `main.cpp` to the Arduino Nano (PlatformIO or Arduino IDE).
2. Connect the Arduino and start the servo power supply.
3. Run:
```bash
python okgarminexploseluilestestiboules.py
```
4. In the preview window, click the 9 sticker positions on the cube face and select the COM port.
5. The robot scans all 6 faces, computes the solution, and solves the cube.

## Project structure

```
CubiCator/
├── main.cpp                              # Arduino firmware
├── okgarminexploseluilestestiboules.py   # Main entry point
├── on_prend_les_couleurs_là.py           # Camera scanning & color acquisition
└── quoicoutasticrousti.py                # Point selector UI (tkinter + OpenCV)
```
