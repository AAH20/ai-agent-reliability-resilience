# Contributing

Contributions should make business outcomes more provable under failure.

1. Open an issue describing the workflow, authoritative destination state and failure boundary.
2. Add or update a versioned experiment contract.
3. Define business invariants, RTO/RPO and financial tolerance.
4. Include a safe path and a negative control.
5. Add tests and run `python -m unittest discover -s tests -v`.
6. Preserve the synthetic-evidence disclaimer in outputs and documentation.

Do not include real credentials, customer data, proprietary policies or experiments against targets without authorization. By contributing, you agree that your contribution is licensed under the MIT License.
