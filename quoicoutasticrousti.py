import cv2
import tkinter as tk
from tkinter import messagebox, ttk
import threading, time
from PIL import Image, ImageTk
import serial.tools.list_ports

MAX_POINTS=9
RADIUS=6
FONT=cv2.FONT_HERSHEY_SIMPLEX


class PointSelectorApp:
    def __init__(self, root, on_validate=None):
        self.root=root
        self.root.title("Sélection de points")
        self.root.configure(bg="#111")
        self.root.resizable(False, False)

        self.on_validate=on_validate
        self.points=[]
        self.running=False
        self.frame=None
        self.lock=threading.Lock()

        self._build_ui()
        self._start_camera()

    def _build_ui(self):
        # ----------------------------------------------------------------------
        # Ligne du haut : sélecteur de port COM + bouton refresh
        # ----------------------------------------------------------------------
        top_frame=tk.Frame(self.root, bg="#111", pady=6)
        top_frame.pack()

        tk.Label(top_frame, text="Port COM :", font=("Consolas", 10),
                 fg="#aaa", bg="#111").pack(side="left", padx=(8, 4))

        self.port_var=tk.StringVar()
        self.port_dropdown=ttk.Combobox(
            top_frame, textvariable=self.port_var,
            state="readonly", width=35, font=("Consolas", 10)
        )
        self.port_dropdown.pack(side="left", padx=(0, 4))
        self._refresh_ports()  # Remplir la liste au démarrage

        tk.Button(top_frame, text="↻", command=self._refresh_ports,
                  bg="#555", fg="white", relief="flat", padx=6, pady=2,
                  cursor="hand2", font=("Consolas", 11)).pack(side="left", padx=(0, 8))

        # ----------------------------------------------------------------------
        # Compteur de points
        # ----------------------------------------------------------------------
        self.status_lbl=tk.Label(
            self.root, text="0 / 9 points",
            font=("Consolas", 11), fg="#aaa", bg="#111"
        )
        self.status_lbl.pack(pady=(0, 4))

        # ----------------------------------------------------------------------
        # Canvas caméra
        # ----------------------------------------------------------------------
        self.canvas=tk.Label(self.root, bg="#000", cursor="crosshair")
        self.canvas.pack()
        self.canvas.bind("<Button-1>", self._on_click)

        # ----------------------------------------------------------------------
        # Boutons du bas
        # ----------------------------------------------------------------------
        btn_frame=tk.Frame(self.root, bg="#111", pady=6)
        btn_frame.pack()
        tk.Button(btn_frame, text="Annuler dernier", command=self._undo,
                  bg="#555", fg="white", relief="flat", padx=10, pady=4,
                  cursor="hand2").pack(side="left", padx=6)
        tk.Button(btn_frame, text="Réinitialiser", command=self._reset,
                  bg="#555", fg="white", relief="flat", padx=10, pady=4,
                  cursor="hand2").pack(side="left", padx=6)
        tk.Button(btn_frame, text="✔  Valider", command=self._validate,
                  bg="#00b44d", fg="white", relief="flat", padx=10, pady=4,
                  cursor="hand2").pack(side="left", padx=6)

    def _refresh_ports(self):
        # Détecte les ports COM disponibles et met à jour la liste déroulante
        # Affiche "COMx (Nom)", stocke le mapping label → device
        # On filtre les ports virtuels Bluetooth (hwid == n/a) qui ne correspondent à rien de branché
        detected=[p for p in serial.tools.list_ports.comports() if p.hwid != 'n/a']
        self._port_map={f"{p.device} ({p.description[:30]})": p.device for p in detected}
        labels=list(self._port_map.keys())
        self.port_dropdown["values"]=labels
        if labels:
            # On garde la sélection actuelle si elle est toujours dispo, sinon on prend la première
            if self.port_var.get() not in labels:
                self.port_var.set(labels[0])
        else:
            self.port_var.set("")

    def _start_camera(self):
        self.cap=cv2.VideoCapture(0, cv2.CAP_DSHOW)

        if not self.cap.isOpened():
            messagebox.showerror("Erreur", "Impossible d'ouvrir la caméra.")
            return

        self.running=True

        self.thread=threading.Thread(
            target=self._feed_loop,
            daemon=True
        )

        self.thread.start()
        self._poll_frame()

    def _feed_loop(self):
        # Tourne en arrière-plan, lit les frames en continu
        while self.running:
            ret, frame=self.cap.read()
            if not ret:
                time.sleep(0.01)
                continue
            frame=cv2.flip(frame, 1)
            with self.lock:
                self.frame=frame.copy()

    def _poll_frame(self):
        # Appelé toutes les 15ms par tkinter pour rafraîchir l'affichage
        if not self.running:
            return
        with self.lock:
            frame=self.frame.copy() if self.frame is not None else None
        if frame is not None:
            self._update_canvas(self._draw_points(frame))
        self.after_id=self.root.after(15, self._poll_frame)

    def _draw_points(self, frame):
        # Dessine les points cliqués sur la frame
        out=frame.copy()
        for (x, y) in self.points:
            cv2.circle(out, (x, y), RADIUS+2, (255, 255, 255), 1)
            cv2.circle(out, (x, y), RADIUS, (0, 200, 255), -1)
        cv2.putText(out, f"{len(self.points)}/9", (10, 24),
                    FONT, 0.7, (255, 255, 255), 2)
        return out

    def _update_canvas(self, frame):
        rgb=cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        imgtk=ImageTk.PhotoImage(image=Image.fromarray(rgb))
        self.canvas.imgtk=imgtk
        self.canvas.configure(image=imgtk)

    def _on_click(self, event):
        if len(self.points) >= MAX_POINTS:
            return
        self.points.append((event.x, event.y))
        self.status_lbl.config(text=f"{len(self.points)} / 9 points")

    def _reset(self):
        self.points.clear()
        self.status_lbl.config(text="0 / 9 points")

    def _undo(self):
        if self.points:
            self.points.pop()
            self.status_lbl.config(text=f"{len(self.points)} / 9 points")

    def _validate(self):
        if not self.points:
            messagebox.showwarning("Aucun point", "Placez au moins un point.")
            return
        if not self.port_var.get():
            messagebox.showwarning("Port COM", "Sélectionnez un port COM.")
            return
        pts=list(self.points)
        port=self._port_map[self.port_var.get()]  # On extrait "COMx" depuis "COMx (Nom)"
        self.on_close()
        if self.on_validate:
            self.on_validate(pts, port)

    def on_close(self):
        self.running=False
        if hasattr(self, "after_id"):
            self.root.after_cancel(self.after_id)
        if hasattr(self, "thread"):
            self.thread.join(timeout=1)
        if self.cap:
            self.cap.release()
        self.root.destroy()


def select_points():
    # Ouvre la fenêtre et retourne (points, port) :
    #   points : 9 points triés pour une grille 3x3 [BG,BM,BD, MG,MM,MD, HG,HM,HD]
    #   port   : port COM sélectionné (ex: "COM3")
    result_pts=[]
    result_port=[]

    def _cb(pts, port):
        result_pts.extend(pts)
        result_port.append(port)

    root=tk.Tk()
    app=PointSelectorApp(root, on_validate=_cb)
    root.protocol("WM_DELETE_WINDOW", app.on_close)
    root.mainloop()

    # Tri : 3 rangées (bas = y fort → haut = y faible), 3 colonnes (gauche→droite)
    pts=sorted(result_pts, key=lambda p: -p[1])   # y décroissant → bas en premier
    row0=sorted(pts[0:3], key=lambda p: p[0])     # rangée bas
    row1=sorted(pts[3:6], key=lambda p: p[0])     # rangée milieu
    row2=sorted(pts[6:9], key=lambda p: p[0])     # rangée haut
    return row0+row1+row2, result_port[0]          # ([BG,BM,BD, MG,MM,MD, HG,HM,HD], "COMx")