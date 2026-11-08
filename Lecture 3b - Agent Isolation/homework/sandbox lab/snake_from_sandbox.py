"""A small Snake game built with Python's standard-library tkinter."""

import random
import tkinter as tk

CELL_SIZE = 20
GRID_WIDTH = 24
GRID_HEIGHT = 20
TICK_MS = 120


class SnakeGame:
    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.root.title("Snake")
        self.root.resizable(False, False)

        self.canvas = tk.Canvas(
            root,
            width=GRID_WIDTH * CELL_SIZE,
            height=GRID_HEIGHT * CELL_SIZE,
            background="#17212b",
            highlightthickness=0,
        )
        self.canvas.pack()
        self.status = tk.Label(root, text="", font=("TkDefaultFont", 11), pady=6)
        self.status.pack()

        self.root.bind("<Up>", lambda _event: self.turn(0, -1))
        self.root.bind("<Down>", lambda _event: self.turn(0, 1))
        self.root.bind("<Left>", lambda _event: self.turn(-1, 0))
        self.root.bind("<Right>", lambda _event: self.turn(1, 0))
        self.root.bind("<w>", lambda _event: self.turn(0, -1))
        self.root.bind("<s>", lambda _event: self.turn(0, 1))
        self.root.bind("<a>", lambda _event: self.turn(-1, 0))
        self.root.bind("<d>", lambda _event: self.turn(1, 0))
        self.root.bind("<r>", lambda _event: self.restart())
        self.restart()

    def restart(self) -> None:
        center = (GRID_WIDTH // 2, GRID_HEIGHT // 2)
        self.snake = [center, (center[0] - 1, center[1]), (center[0] - 2, center[1])]
        self.direction = (1, 0)
        self.next_direction = self.direction
        self.score = 0
        self.game_over = False
        self.food = self.place_food()
        self.draw()
        self.schedule_tick()

    def place_food(self) -> tuple[int, int] | None:
        empty = [
            (x, y)
            for x in range(GRID_WIDTH)
            for y in range(GRID_HEIGHT)
            if (x, y) not in self.snake
        ]
        return random.choice(empty) if empty else None

    def turn(self, dx: int, dy: int) -> None:
        if not self.game_over and (dx, dy) != (-self.direction[0], -self.direction[1]):
            self.next_direction = (dx, dy)

    def schedule_tick(self) -> None:
        self.root.after(TICK_MS, self.tick)

    def tick(self) -> None:
        if self.game_over:
            return

        self.direction = self.next_direction
        head_x, head_y = self.snake[0]
        dx, dy = self.direction
        new_head = (head_x + dx, head_y + dy)
        eating = new_head == self.food
        body = self.snake if eating else self.snake[:-1]

        if (
            not 0 <= new_head[0] < GRID_WIDTH
            or not 0 <= new_head[1] < GRID_HEIGHT
            or new_head in body
        ):
            self.game_over = True
            self.draw()
            return

        self.snake.insert(0, new_head)
        if eating:
            self.score += 1
            self.food = self.place_food()
            if self.food is None:
                self.game_over = True
        else:
            self.snake.pop()

        self.draw()
        if not self.game_over:
            self.schedule_tick()

    def draw_cell(self, cell: tuple[int, int], color: str) -> None:
        x, y = cell
        inset = 2
        self.canvas.create_rectangle(
            x * CELL_SIZE + inset,
            y * CELL_SIZE + inset,
            (x + 1) * CELL_SIZE - inset,
            (y + 1) * CELL_SIZE - inset,
            fill=color,
            outline="",
        )

    def draw(self) -> None:
        self.canvas.delete("all")
        if self.food is not None:
            self.draw_cell(self.food, "#ff5c5c")
        for index, segment in enumerate(self.snake):
            self.draw_cell(segment, "#9be564" if index == 0 else "#54c46a")

        self.status.config(text=f"Score: {self.score}    Arrow keys / WASD to move    R to restart")
        if self.game_over:
            self.canvas.create_text(
                GRID_WIDTH * CELL_SIZE // 2,
                GRID_HEIGHT * CELL_SIZE // 2,
                text=f"Game over!  Score: {self.score}\nPress R to play again",
                fill="white",
                font=("TkDefaultFont", 18, "bold"),
                justify="center",
            )


def main() -> None:
    root = tk.Tk()
    SnakeGame(root)
    root.mainloop()


if __name__ == "__main__":
    main()
