# Earth shadow: cylindrical / conical

Sun unit \(\hat{\mathbf s}\) (Vallado low-precision). Night-side when \(\mathbf r\cdot\hat{\mathbf s}<0\).

Penumbra / umbra cone radii at anti-sun distance \(s=-\mathbf r\cdot\hat{\mathbf s}\):

\[
R_\mathrm{pen}=R_\oplus + s\tan\alpha_\mathrm{pen},\quad
R_\mathrm{umb}=R_\oplus - s\tan\alpha_\mathrm{umb}
\]

Shadow function \(\nu\in[0,1]\): 1 sunlit, (0,1) penumbra, 0 umbra. Boundaries via `brentq`.

**References:** Vallado §5.3; Montenbruck & Gill.
