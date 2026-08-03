## How the App was deployed

### Backend

- Containerized the Flask backend using Docker Compose and built the image locally.

- Published the image to Docker Hub for cloud deployment.

-  Created a Google Cloud VM, installed Docker and Docker Compose, and pulled the backend image from Docker Hub.

- Deployed the container on the VM, exposing the API over the VM’s external IP.

#### Backend environment variables

- `RANK_USERNAMES` — comma-separated allowlist of usernames permitted to see the letter-rank
  layer (rank field, rank chip, Ranks table). Read at request time, so a container restart picks
  up a change without a redeploy. Unset means nobody sees ranks; guests never see them regardless
  of this setting. Set in the VM's `~/.env` for production and `backend/.env` for local dev — never
  committed.

### Frontend

- Deployed the React frontend using Netlify for static hosting.

- Configured a redirect rule to route all requests beginning with /api/ to the backend’s external IP on Google Cloud.

- Updated all frontend API calls to use the /api/ prefix to ensure proper request forwarding.


App is deployed on [www.chronologtracker.com](https://chronologtracker.com/)