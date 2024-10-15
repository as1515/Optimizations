
import matplotlib.pyplot as plt
import matplotlib.animation as animation
import numpy as np

class OptimizationVisualizer:
    def __init__(self, objective_values):
        self.objective_values = objective_values
        self.fig, self.ax = plt.subplots()
        self.line, = self.ax.plot([], [], lw=2)
    
    def setup_plot(self):
        self.ax.set_xlim(0, len(self.objective_values))
        self.ax.set_ylim(min(self.objective_values), max(self.objective_values) + 5)
        self.ax.set_xlabel('Iteration')
        self.ax.set_ylabel('Profit')
    
    def init(self):
        self.line.set_data([], [])
        return (self.line,)

    def animate(self, i):
        x = np.arange(i)
        y = self.objective_values[:i]
        self.line.set_data(x, y)
        return (self.line,)

    def run_animation(self):
        self.setup_plot()
        ani = animation.FuncAnimation(
            self.fig, self.animate, init_func=self.init, 
            frames=len(self.objective_values), interval=1000, blit=True
        )
        plt.show()

class OptimizationPlotter:
    def __init__(self, objective_values):
        self.objective_values = objective_values

    def plot_progress(self):
        plt.plot(self.objective_values, marker='o', linestyle='-', linewidth=2)
        plt.xlabel('Iteration')
        plt.ylabel('Profit')
        plt.title('Optimization Progress')
        plt.grid(True)
        plt.show()
