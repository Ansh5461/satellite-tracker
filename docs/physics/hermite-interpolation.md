# Cubic Hermite dead-reckoning

Between keyframes \((\mathbf r_0,\mathbf v_0,t_0)\) and \((\mathbf r_1,\mathbf v_1,t_1)\), \(u=(t-t_0)/(t_1-t_0)\), \(\Delta t=t_1-t_0\):

\[
\mathbf r(u)=h_{00}(u)\mathbf r_0 + h_{10}(u)\mathbf v_0\Delta t + h_{01}(u)\mathbf r_1 + h_{11}(u)\mathbf v_1\Delta t
\]

with standard Hermite basis polynomials. Render delay \(\sim 1.5\) ticks absorbs jitter; \(u\) clamped on packet loss.

**References:** computer graphics / numerical analysis texts on cubic Hermite splines.
