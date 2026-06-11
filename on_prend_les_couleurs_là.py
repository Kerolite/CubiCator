import cv2, serial, time
import numpy as np
from quoicoutasticrousti import select_points


def wait_for_arduino(ser):
    # Bloque jusqu'à recevoir "OK" de l'Arduino
    while True:
        if ser.in_waiting:
            msg=ser.readline().decode().strip()
            print("Arduino :", msg)
            if msg=="OK":
                return


def get_colors():
    # ------------------------------------------------------------------------------
    # Scanne les 6 faces du cube et retourne les couleurs RGB de chaque case.
    # L'utilisateur sélectionne les 9 points une seule fois (face 1), ils sont
    # réutilisés pour les 5 faces suivantes car la caméra ne bouge pas.
    # Le port COM est également sélectionné dans la même fenêtre.
    #
    # Retourne :
    #   all_colors : liste de 6 listes de 9 tuples (r,g,b), dans l'ordre U/R/F/D/L/B
    #   centers    : liste de 6 tuples (r,g,b), couleur du centre de chaque face (index 4)
    # ------------------------------------------------------------------------------
    points, com=select_points()  # L'utilisateur clique les 9 cases et choisit le port COM
    ser=serial.Serial(com, 9600, timeout=1)
    time.sleep(2)
    accuracy=30             # Taille en pixels de la zone de capture autour de chaque point
    cap=cv2.VideoCapture(0)

    all_colors=[]

    for j in range(6):
        ret, frame=cap.read()
        frame = cv2.flip(frame, 1)

        colors=[]

        for point in points:
            x, y=point

            cell=frame[y:y+accuracy, x:x+accuracy]

            if cell.size > 0:
                median_color=np.median(cell.reshape(-1, 3), axis=0).astype(int)

                b, g, r=median_color

                colors.append((r, g, b))

                # Affichage : carré plein de la couleur détectée + contour blanc
                cv2.rectangle(
                    frame,
                    (x, y),
                    (x+accuracy, y+accuracy),
                    (int(b), int(g), int(r)),
                    -1
                )
                cv2.rectangle(
                    frame,
                    (x, y),
                    (x+accuracy, y+accuracy),
                    (255, 255, 255),
                    2
                )

        cv2.imshow("Frame", frame)
        cv2.waitKey(1)                                    # Juste pour rafraîchir la fenêtre
        cv2.imwrite(f"CubiCator/images/face{j+1}.png", frame)

        all_colors.append(colors)

        # On demande à l'Arduino de tourner le cube, sauf après la dernière face
        if j < 5:
            ser.write(b"NEXT\n")
            wait_for_arduino(ser)                         # Bloque jusqu'au "OK" de l'Arduino

    cap.release()
    ser.close()
    cv2.destroyAllWindows()

    # Le centre de chaque face = index 4 (case du milieu dans la grille 3x3)
    centers=[face[4] for face in all_colors]

    return all_colors, centers, com, ser