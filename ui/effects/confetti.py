"""Efecto de confeti no bloqueante para la interfaz Tkinter."""

from __future__ import annotations

import math
import random

import tkinter as tk


def start_confetti_burst(
    root: tk.Misc,
    screen_x: int,
    screen_y: int,
    *,
    enabled: bool = True,
    particles_per_frame: int = 6,
    frame_delay_ms: int = 16,
    max_frames: int = 60,
) -> None:
    """Dispara una ráfaga de confeti utilizando ``after`` para ~60 FPS.

    Los círculos creados se etiquetan como ``confetti`` y se eliminan al final
    de la animación para liberar recursos. Se generan unas pocas partículas por
    cuadro para minimizar operaciones sobre el lienzo.
    """

    if not enabled:
        return

    if root is None or not root.winfo_exists():
        return

    canvas = tk.Canvas(
        root,
        highlightthickness=0,
        bd=0,
        bg=root.cget("bg"),
    )
    canvas.place(x=0, y=0, relwidth=1, relheight=1)
    canvas.lift()

    origin_x = screen_x - root.winfo_rootx()
    origin_y = screen_y - root.winfo_rooty()

    particles: list[dict[str, float | int]] = []
    palette = [
        "#ff9f1c",
        "#ff595e",
        "#8ac926",
        "#1982c4",
        "#6a4c93",
        "#f4d35e",
    ]
    gravity = 0.35
    drag = 0.98

    def spawn_particles() -> None:
        for _ in range(particles_per_frame):
            angle = random.uniform(0, 2 * math.pi)
            speed = random.uniform(3, 7)
            vx = math.cos(angle) * speed
            vy = math.sin(angle) * speed - 3
            size = random.randint(3, 6)
            color = random.choice(palette)
            particle_id = canvas.create_oval(
                origin_x - size,
                origin_y - size,
                origin_x + size,
                origin_y + size,
                fill=color,
                outline="",
                tags=("confetti",),
            )
            particles.append({"id": particle_id, "vx": vx, "vy": vy, "size": size})

    def update_particles() -> None:
        for particle in particles:
            particle["vy"] = (particle["vy"] + gravity) * drag
            particle["vx"] *= drag
            canvas.move(particle["id"], particle["vx"], particle["vy"])

    def confetti_burst(step: int = 0) -> None:
        if not (root.winfo_exists() and canvas.winfo_exists()):
            return
        if step >= max_frames:
            canvas.delete("confetti")
            particles.clear()
            canvas.after(0, canvas.destroy)
            return

        spawn_particles()
        update_particles()
        root.after(frame_delay_ms, confetti_burst, step + 1)

    confetti_burst()


# Alias conservado para compatibilidad con llamadas existentes
ConfettiBurst = start_confetti_burst


def maybe_start_confetti(*args, enabled: bool = True, **kwargs) -> None:
    """Ejecuta ``start_confetti_burst`` sólo si está habilitado."""

    if not enabled:
        return
    start_confetti_burst(*args, enabled=enabled, **kwargs)
