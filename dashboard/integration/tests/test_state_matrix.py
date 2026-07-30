from __future__ import annotations

import unittest

from dashboard.integration.state_matrix import run_state_matrix


class RealStateMatrixTests(unittest.TestCase):
    def test_real_backend_to_frontend_abnormal_state_matrix(self):
        run_state_matrix()


if __name__ == "__main__":
    unittest.main()
