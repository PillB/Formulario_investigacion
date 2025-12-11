"""Efecto de confeti no bloqueante para la interfaz Tkinter."""

from __future__ import annotations

import math
import random
import weakref
from contextlib import suppress

import tkinter as tk

_PARTICLE_SESSION_CAP = 30
_MAX_BURST_DURATION_MS = 1300
_remaining_particle_budget = _PARTICLE_SESSION_CAP
_scheduled_confetti_jobs: list[tuple[weakref.ReferenceType[tk.Misc], str]] = []


def _register_confetti_job(root: tk.Misc, delay_ms: int, callback) -> str | None:
    try:
        after_id = root.after(delay_ms, callback)
    except tk.TclError:
        return None
    _scheduled_confetti_jobs.append((weakref.ref(root), after_id))
    return after_id


def _forget_confetti_job(after_id: str | None) -> None:
    if not after_id:
        return
    for index, (_, job_id) in enumerate(list(_scheduled_confetti_jobs)):
        if job_id == after_id:
            _scheduled_confetti_jobs.pop(index)
            break


def cancel_confetti_jobs(root: tk.Misc | None = None) -> None:
    """Cancela callbacks pendientes del confeti, por ejemplo al cerrar la ventana."""

    for job_root_ref, job_id in list(_scheduled_confetti_jobs):
        job_root = job_root_ref()
        if job_root is None:
            _scheduled_confetti_jobs.remove((job_root_ref, job_id))
            continue
        if root is None or root is job_root:
            with suppress(tk.TclError):
                job_root.after_cancel(job_id)
            _scheduled_confetti_jobs.remove((job_root_ref, job_id))


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

    global _remaining_particle_budget

    if not enabled or _remaining_particle_budget <= 0:
        return

    if root is None or not root.winfo_exists():
        return

    frame_delay_ms = max(1, frame_delay_ms)
    max_frames = min(
        max_frames,
        max(1, math.ceil(_MAX_BURST_DURATION_MS / frame_delay_ms)),
    )

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
        global _remaining_particle_budget

        if _remaining_particle_budget <= 0:
            return

        batch_size = min(particles_per_frame, _remaining_particle_budget)
        _remaining_particle_budget = max(0, _remaining_particle_budget - batch_size)
        for _ in range(batch_size):
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

    def _destroy_canvas() -> None:
        with suppress(tk.TclError):
            canvas.delete("confetti")
            particles.clear()
            canvas.destroy()

    def _schedule_next(step: int) -> None:
        after_id: str | None = None

        def _runner(job_id: str | None = None) -> None:
            confetti_burst(step, job_id)

        def _callback() -> None:
            _runner(after_id)

        if not (root.winfo_exists() and canvas.winfo_exists()):
            return
        after_id = _register_confetti_job(root, frame_delay_ms, _callback)

    def confetti_burst(step: int = 0, scheduled_id: str | None = None) -> None:
        _forget_confetti_job(scheduled_id)

        try:
            if not (root.winfo_exists() and canvas.winfo_exists()):
                cancel_confetti_jobs(root)
                return
        except tk.TclError:
            cancel_confetti_jobs(root)
            return

        if step >= max_frames:
            _destroy_canvas()
            return

        spawn_particles()
        update_particles()

        if (not particles and _remaining_particle_budget <= 0) or step + 1 >= max_frames:
            _destroy_canvas()
            return

        _schedule_next(step + 1)

    confetti_burst()


# Alias conservado para compatibilidad con llamadas existentes
ConfettiBurst = start_confetti_burst


def maybe_start_confetti(*args, enabled: bool = True, **kwargs) -> None:
    """Ejecuta ``start_confetti_burst`` sólo si está habilitado."""

    if not enabled:
        return
    start_confetti_burst(*args, enabled=enabled, **kwargs)
