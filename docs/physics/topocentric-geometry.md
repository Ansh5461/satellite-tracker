# Topocentric ENU / SEZ geometry

Observer ECEF/ITRS from WGS-84:

\[
\mathbf r_\mathrm{obs} = \bigl((N+h)\cos\phi\cos\lambda,\;(N+h)\cos\phi\sin\lambda,\;\bigl(N(1-e^2)+h\bigr)\sin\phi\bigr)
\]

Range \(\boldsymbol\rho=\mathbf r_\mathrm{sat}-\mathbf r_\mathrm{obs}\). ENU:

\[
\begin{bmatrix}e\\n\\u\end{bmatrix}=T_\mathrm{ENU}(\phi,\lambda)\,\boldsymbol\rho,\quad
\mathrm{Az}=\mathrm{atan2}(e,n),\;
\mathrm{El}=\mathrm{atan2}(u,\sqrt{e^2+n^2})
\]

Range rate \(\dot\rho=\hat{\boldsymbol\rho}\cdot\mathbf v_\mathrm{sat}\) (fixed site).

**References:** Vallado §4.4; Montenbruck & Gill, *Satellite Orbits*.
