# Torque-free CubeSat attitude

Euler equations (principal axes):

\[
I_x\dot\omega_x=(I_y-I_z)\omega_y\omega_z\quad(\mathrm{cyclic})
\]

Quaternion kinematics \(\dot q=\tfrac12 q\otimes\omega\). Integrated with `solve_ivp` (DOP853).

Solar power \(P=P_0\sum_i\max(0,\hat n_i\cdot\hat s)\,\nu\). Polarization mismatch for linear-linear: \(-10\log_{10}(\cos^2\psi)\).

**References:** Wertz, *Spacecraft Attitude Determination and Control*.
