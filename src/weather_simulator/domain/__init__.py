"""Rules settled in CLAUDE.md section 3: sky class, thresholds, bias correction.

This layer is meant to be stable. The sky class is derived here, by a single
function called for both the past and the future segments — duplicating that
logic would reopen the divergence at the seam that section 3 exists to prevent.
"""
