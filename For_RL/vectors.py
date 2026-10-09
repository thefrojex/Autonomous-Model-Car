import matplotlib.pyplot as plt
import numpy as np

# Define origin and vectors
origin = np.array([[0, 0]])  # origin point
v1 = np.array([[3, 2]])      # vector 1
v2 = np.array([[1, -1]])     # vector 2 (optional)

# Plot vectors using quiver
plt.quiver(*origin.T, *v1.T, color='r', angles='xy', scale_units='xy', scale=1, label='v1')
plt.quiver(*origin.T, *v2.T, color='b', angles='xy', scale_units='xy', scale=1, label='v2')

# Axes settings
plt.xlim(-2, 5)
plt.ylim(-2, 5)
plt.grid()
plt.axhline(0, color='black', linewidth=0.5)
plt.axvline(0, color='black', linewidth=0.5)
plt.gca().set_aspect('equal')
plt.legend()
plt.title("2D Vector Plot")
plt.show()
