# TEME → PEF → ITRS

SGP4 outputs \(\mathbf r_\mathrm{TEME}\), \(\mathbf v_\mathrm{TEME}\).

**GMST82** (Vallado Alg. 3-5 family):

\[
\theta_\mathrm{GMST} = f(T_\mathrm{UT1})
\]

\[
\mathbf r_\mathrm{PEF} = R_3(\theta_\mathrm{GMST})\,\mathbf r_\mathrm{TEME}
\]

\[
\mathbf v_\mathrm{PEF} = R_3(\theta_\mathrm{GMST})\,\mathbf v_\mathrm{TEME} + \boldsymbol\omega_\oplus\times\mathbf r_\mathrm{PEF}
\]

with \(\boldsymbol\omega_\oplus=[0,0,7.292115\times10^{-5}]^\top\) rad/s.

Polar motion:

\[
\mathbf r_\mathrm{ITRS} = W(x_p,y_p)\,\mathbf r_\mathrm{PEF},\quad
W \approx R_2(x_p)R_1(y_p)
\]

**References:** Vallado 4th ed. §3.7; astropy `TEME`→`ITRS`.
