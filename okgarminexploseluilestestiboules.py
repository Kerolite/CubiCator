import kociemba, time, serial, math

def send_to_arduino(moves: list, ser: serial.Serial):
    move_str = ''.join(moves)
    payload = (move_str + '\n').encode()
    ser.reset_input_buffer()
    ser.write(payload)
    print(f"Sent ({len(moves)}) moves : {move_str}")
    
    deadline = time.time() + 10
    while time.time() < deadline:
        if ser.in_waiting:
            line = ser.readline().decode().strip()
            print(f"Arduino : {line}")
            if line == "OK":
                print("Arduino successfully received the moves.")
                return
    print("No response (timeout)")


# ------------------------------------------------------------------------------
# ONLY USED TO MOCK THE CAMERA
# ------------------------------------------------------------------------------
from random import choice
import copy

MOVES=['U', "U'", 'U2', 'D', "D'", 'D2',
       'R', "R'", 'R2', 'L', "L'", 'L2',
       'F', "F'", 'F2', 'B', "B'", 'B2']

# Cube résolu : [U, R, F, D, L, B], centre = couleur de la face
# Ordre des faces : 0=U(W), 1=R(R), 2=F(G), 3=D(Y), 4=L(O), 5=B(B)
SOLVED=[
    [['W','W','W'],['W','W','W'],['W','W','W']],  # U
    [['R','R','R'],['R','R','R'],['R','R','R']],  # R
    [['G','G','G'],['G','G','G'],['G','G','G']],  # F
    [['Y','Y','Y'],['Y','Y','Y'],['Y','Y','Y']],  # D
    [['O','O','O'],['O','O','O'],['O','O','O']],  # L
    [['B','B','B'],['B','B','B'],['B','B','B']],  # B
]


def apply_move(cube, move):
    c=copy.deepcopy(cube)
    U, R, F, D, L, B=0, 1, 2, 3, 4, 5

    def rotate_face_cw(f):
        # Rotation 90° horaire d'une face (tableau 3x3)
        c[f]=[
            [c[f][2][0], c[f][1][0], c[f][0][0]],
            [c[f][2][1], c[f][1][1], c[f][0][1]],
            [c[f][2][2], c[f][1][2], c[f][0][2]],
        ]

    base=move.replace("'", "").replace("2", "")
    times=3 if "'" in move else (2 if "2" in move else 1)  # ' = 3x horaire, 2 = 2x

    for _ in range(times):
        if base=='U':
            rotate_face_cw(U)
            tmp=[c[F][0][0], c[F][0][1], c[F][0][2]]
            c[F][0]=[c[R][0][0], c[R][0][1], c[R][0][2]]
            c[R][0]=[c[B][0][0], c[B][0][1], c[B][0][2]]
            c[B][0]=[c[L][0][0], c[L][0][1], c[L][0][2]]
            c[L][0]=tmp
        elif base=='D':
            rotate_face_cw(D)
            tmp=[c[F][2][0], c[F][2][1], c[F][2][2]]
            c[F][2]=[c[L][2][0], c[L][2][1], c[L][2][2]]
            c[L][2]=[c[B][2][0], c[B][2][1], c[B][2][2]]
            c[B][2]=[c[R][2][0], c[R][2][1], c[R][2][2]]
            c[R][2]=tmp
        elif base=='R':
            rotate_face_cw(R)
            for row in range(3):
                tmp=c[U][row][2]
                c[U][row][2]=c[F][row][2]
                c[F][row][2]=c[D][row][2]
                c[D][row][2]=c[B][2-row][0]
                c[B][2-row][0]=tmp
        elif base=='L':
            rotate_face_cw(L)
            for row in range(3):
                tmp=c[U][row][0]
                c[U][row][0]=c[B][2-row][2]
                c[B][2-row][2]=c[D][row][0]
                c[D][row][0]=c[F][row][0]
                c[F][row][0]=tmp
        elif base=='F':
            rotate_face_cw(F)
            tmp=[c[U][2][0], c[U][2][1], c[U][2][2]]
            c[U][2][0], c[U][2][1], c[U][2][2]=c[L][2][2], c[L][1][2], c[L][0][2]  # L col droite (bas→haut) → U rangée bas
            c[L][0][2], c[L][1][2], c[L][2][2]=c[D][0][0], c[D][0][1], c[D][0][2]  # D rangée haut → L col droite (haut→bas)
            c[D][0][0], c[D][0][1], c[D][0][2]=c[R][2][0], c[R][1][0], c[R][0][0]  # R col gauche (bas→haut) → D rangée haut
            c[R][0][0], c[R][1][0], c[R][2][0]=tmp[0], tmp[1], tmp[2]               # U rangée bas → R col gauche (haut→bas)
        elif base=='B':
            rotate_face_cw(B)
            tmp=[c[U][0][0], c[U][0][1], c[U][0][2]]
            c[U][0][0], c[U][0][1], c[U][0][2]=c[R][0][2], c[R][1][2], c[R][2][2]  # R col droite (haut→bas) → U rangée haut
            c[R][0][2], c[R][1][2], c[R][2][2]=c[D][2][2], c[D][2][1], c[D][2][0]  # D rangée bas (droite→gauche) → R col droite
            c[D][2][0], c[D][2][1], c[D][2][2]=c[L][0][0], c[L][1][0], c[L][2][0]  # L col gauche (haut→bas) → D rangée bas
            c[L][0][0], c[L][1][0], c[L][2][0]=tmp[2], tmp[1], tmp[0]               # U rangée haut (droite→gauche) → L col gauche
    return c


def generate_scrambled_cube(n_moves=20):
    # Génère un cube mélangé en appliquant n_moves mouvements aléatoires
    cube=copy.deepcopy(SOLVED)
    sequence=[]
    for _ in range(n_moves):
        move=choice(MOVES)
        cube=apply_move(cube, move)
        sequence.append(move)
    return cube, sequence


# ------------------------------------------------------------------------------
# COLOR → FACE CONVERSION
# ------------------------------------------------------------------------------

def color_distance(c1, c2):
    # Distance euclidienne entre deux couleurs RGB
    return math.sqrt(sum((a-b)**2 for a, b in zip(c1, c2)))


def build_kociemba_string(all_colors: list, centers: list):
    # ------------------------------------------------------------------------------
    # Convertit les 54 couleurs RGB en string Kociemba (54 lettres U/R/F/D/L/B).
    # Pour chaque case, on cherche le centre dont la couleur RGB est la plus proche
    # par distance euclidienne → la case appartient à cette face.
    #
    # all_colors : liste de 6 listes de 9 tuples (r,g,b), dans l'ordre U/R/F/D/L/B
    # centers    : liste de 6 tuples (r,g,b), couleur du centre de chaque face
    # ------------------------------------------------------------------------------
    faces=['U', 'R', 'F', 'D', 'L', 'B']
    suite=""

    for face_idx in range(6):
        for case_idx, case_color in enumerate(all_colors[face_idx]):
            best_face=None
            best_dist=float('inf')
            for center_idx, center_color in enumerate(centers):
                dist=color_distance(case_color, center_color)
                if dist < best_dist:
                    best_dist=dist
                    best_face=center_idx
            suite+=faces[best_face]
            print(f"Face {faces[face_idx]}, case {case_idx} : RGB{case_color} → {faces[best_face]} (dist={best_dist:.1f})")

    return suite


# ------------------------------------------------------------------------------
# CUBE SOLVER
# ------------------------------------------------------------------------------

def solve_and_export(suite: str):
    # ------------------------------------------------------------------------------
    # Résout le cube via kociemba et convertit la solution pour l'Arduino :
    #       - Moves horaires (ex: U) restent identiques.
    #       - Moves anti-horaires (ex: U') deviennent 3x le move horaire.
    #       - Moves 180° (ex: U2) deviennent 2x le move horaire.
    # ------------------------------------------------------------------------------
    print(suite)
    print(len(suite))

    solution=kociemba.solve(suite)
    print(solution)

    solution=solution.split(" ")
    print(solution)

    ready_to_export=[]
    for move in solution:
        if move in ['U', 'D', 'R', 'L', 'F', 'B']:
            ready_to_export.append(move)
        elif move in ["U'", "D'", "R'", "L'", "F'", "B'"]:
            for i in range(3):
                ready_to_export.append(move.replace("'", ""))
        elif move in ['U2', 'D2', 'R2', 'L2', 'F2', 'B2']:
            for i in range(2):
                ready_to_export.append(move.replace("2", ""))

    print(f"Move to export : {ready_to_export}")
    return ready_to_export


# ------------------------------------------------------------------------------
# MAIN
# ------------------------------------------------------------------------------

if __name__ == "__main__":
    DEV_MODE = True

    # ------------------------------------------------------------------
    # STEP 1 : ACQUISITION DES COULEURS (CAMERA OU MOCK)
    # ------------------------------------------------------------------
    print("=== Acquisition des couleurs ===")

    if DEV_MODE:
        from on_prend_les_couleurs_là import wait_for_arduino
        print("=== MODE DEV : simulation caméra + Arduino NEXT ===")

        cube, scramble = generate_scrambled_cube(20)
        print("Scramble mock :", " ".join(scramble))

        color_map = {
            'W': (255, 255, 255), 'R': (255, 0, 0), 'G': (0, 255, 0),
            'Y': (255, 255, 0),   'O': (255, 128, 0), 'B': (0, 0, 255),
        }

        all_colors = []
        for face in cube:
            colors = []
            for row in face:
                for sticker in row:
                    colors.append(color_map[sticker])
            all_colors.append(colors)

        centers = [face[4] for face in all_colors]

        com = "COM4"
        ser = serial.Serial(com, 9600, timeout=30)
        time.sleep(2)

        print("Simulating Arduino NEXT sequence:")
        for i in range(6):
            ser.write(b"NEXT\n")
            wait_for_arduino(ser)

    else:
        from on_prend_les_couleurs_là import get_colors
        all_colors, centers, com, ser = get_colors()
        print(f"Centres détectés : {centers}")
    # ------------------------------------------------------------------
    # STEP 2 : CONVERSION COULEURS → STRING KOCIEMBA
    # ------------------------------------------------------------------
    print("=== Conversion couleurs → faces ===")
    suite = build_kociemba_string(all_colors, centers)
    print(f"String Kociemba : {suite}")

    # ------------------------------------------------------------------
    # STEP 3 : RÉSOLUTION
    # ------------------------------------------------------------------
    print("=== Résolution ===")
    ready_to_export = solve_and_export(suite)

    # ------------------------------------------------------------------
    # STEP 4 : ENVOI ARDUINO
    # ------------------------------------------------------------------
    print("=== Envoi Arduino ===")
    send_to_arduino(ready_to_export, ser)
    ser.close()
# ------------------------------------------------------------------------------
# OVER