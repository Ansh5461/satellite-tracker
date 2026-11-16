# Time scales: UTC → UT1 / TT

SGP4’s TEME frame is defined with **GMST82** as a function of **UT1** (Vallado et al. 2006). Relativistic / solar ephemerides use **TT**.

Given timezone-aware UTC \(t\):

\[
\mathrm{UT1} = \mathrm{UTC} + \Delta\mathrm{UT1},\qquad
\mathrm{TT} = \mathrm{TAI} + 32.184\,\mathrm{s}
\]

Julian Date is split \((jd, fr)\) with \(fr\in[0,1)\) for `SatrecArray.sgp4`.

Polar motion \((x_p, y_p)\) from IERS rotates PEF→ITRS. When IERS tables are unavailable the pipeline sets \(\Delta\mathrm{UT1}=0\), \(x_p=y_p=0\) and flags `degraded_iers`.

**References:** Vallado, *Fundamentals of Astrodynamics and Applications*, 4th ed.; IERS Conventions 2010.
