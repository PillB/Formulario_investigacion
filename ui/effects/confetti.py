"""Efectos visuales básicos para la interfaz Tkinter."""

from __future__ import annotations

import math
import random
import tkinter as tk
from typing import Any


class ConfettiBurst:
    """Anima un destello de confeti efímero en la ventana principal.

    La animación se ejecuta en un lienzo temporal que cubre la raíz, con una
    duración aproximada de 60 fotogramas (alrededor de 1 segundo) a 16 ms por
    fotograma. Se generan 60 partículas con trayectorias y colores aleatorios.
    El lienzo se destruye automáticamente al finalizar para evitar fugas de
    widgets.
    """

    def __init__(
        self,
        root: tk.Misc,
        screen_x: int,
        screen_y: int,
        *,
        particle_count: int = 60,
        frame_delay_ms: int = 16,
        max_frames: int = 60,
    ) -> None:
        self.root = root
        self.canvas = tk.Canvas(
            root,
            highlightthickness=0,
            bd=0,
            bg=root.cget("bg"),
        )
        self.canvas.place(x=0, y=0, relwidth=1, relheight=1)
        self.canvas.lift()

        origin_x = screen_x - root.winfo_rootx()
        origin_y = screen_y - root.winfo_rooty()

        self._frame = 0
        self._frame_delay_ms = frame_delay_ms
        self._max_frames = max_frames
        self._particles: list[dict[str, Any]] = []
        self._populate_particles(particle_count, origin_x, origin_y)
        self._animate()

    def _populate_particles(self, count: int, origin_x: float, origin_y: float) -> None:
        palette = [
            "#ff9f1c",
            "#ff595e",
            "#8ac926",
            "#1982c4",
            "#6a4c93",
            "#f4d35e",
        ]
        for _ in range(count):
            angle = random.uniform(0, 2 * math.pi)
            speed = random.uniform(3, 7)
            vx = math.cos(angle) * speed
            vy = math.sin(angle) * speed - 3
            size = random.randint(3, 6)
            color = random.choice(palette)
            particle_id = self.canvas.create_oval(
                origin_x - size,
                origin_y - size,
                origin_x + size,
                origin_y + size,
                fill=color,
                outline="",
            )
            self._particles.append(
                {
                    "id": particle_id,
                    "x": origin_x,
                    "y": origin_y,
                    "vx": vx,
                    "vy": vy,
                    "size": size,
                }
            )

    def _animate(self) -> None:
        if not self.canvas.winfo_exists():
            return
        if self._frame >= self._max_frames:
            self.canvas.after(0, self.canvas.destroy)
            return

        gravity = 0.35
        drag = 0.98
        for particle in self._particles:
            particle["vy"] += gravity
            particle["vx"] *= drag
            particle["vy"] *= drag
            particle["x"] += particle["vx"]
            particle["y"] += particle["vy"]
            size = particle["size"]
            self.canvas.coords(
                particle["id"],
                particle["x"] - size,
                particle["y"] - size,
                particle["x"] + size,
                particle["y"] + size,
            )

        self._frame += 1
        self.canvas.after(self._frame_delay_ms, self._animate)
