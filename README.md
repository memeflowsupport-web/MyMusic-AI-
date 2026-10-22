# MyMusic AI

An independent music-AI and infrastructure project. The long-term goal is to develop and operate our own music-generation model and supporting services, rather than relying on a paid third-party music-generation API.

## Current status
**Milestone 1: Static frontend foundation.** The first page is a responsive landing-page preview. Music generation is intentionally not implemented yet; the interface does not claim to generate audio.

## Principles
- Phone-first project management through GitHub.
- Minimize ongoing costs and external dependencies.
- Use open-source components where sensible.
- Keep model training, inference, database, and storage portable.
- Use only training data with documented rights suitable for intended use.
- Never commit passwords, access tokens, private keys, or production secrets.
- Make feature status and limitations clear.

## Planned architecture
- Frontend: static HTML/CSS/JavaScript initially.
- Backend: Python API service, to be designed after the frontend milestone.
- Database: PostgreSQL, self-hostable.
- Audio storage: portable storage adapter.
- Job queue: background generation jobs with status tracking.
- Music AI: research and experiments first; no production model selected yet.
- Deployment: free static preview if suitable. Static hosting does not run the backend or AI model.

## Roadmap
1. Responsive public landing page.
2. Architecture, security and testing documentation.
3. Backend and database design.
4. Storage and job queue prototypes.
5. Music-model research, dataset licensing review and small experiments.
6. Connect a tested model to the application.
7. Production readiness, monitoring, backups and deployment.

## Preview
Open index.html in a browser. No framework, package installation, API key, database, or external music-generation API is needed.

## Hosting note
GitHub Pages can serve static files, but it does not execute a Python backend or train/run a music model. Review current provider policies and limits before using it for a commercial or SaaS product. Keep the frontend portable.

## Security
Never place credentials in browser JavaScript or commit them to this repository. Private operations must be enforced by a backend.

## License
No project-wide software or model license has been selected yet. Do not assume the project or future model is open for reuse until a license is added. Review third-party dependencies and datasets individually.
