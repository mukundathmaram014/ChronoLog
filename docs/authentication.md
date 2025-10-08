- [How JWT authentication works](#how-jwt-authentication-works)
  - [General JWT Authentication](#general-jwt-authentication)
  - [Refresh tokens](#refresh-tokens)
  - [Cross Site Request Forgery(CSRF) Protection](#cross-site-request-forgerycsrf-protection)
- [How JWT authentication is Implemented in App](#how-jwt-authentication-is-implemented-in-app)
  - [Backend Auth Implementation](#backend-auth-implementation)
  - [Logout user implementation](#logout-user-implementation)
  - [Frontend Auth Implementation](#frontend-auth-implementation)

## How JWT authentication works

### General JWT Authentication

JWT authentication is a secure way of authenticating users that log into your application. It uses JSON Web tokens which are compact verifiable JSON objects used to transmit variable claims securely between parties. The Way it works is that there is an access token and a refresh token. Access token is how user is actually authenticated. When user logs in, backend creates an access token and sends this in the successful login response. Frontend stores this access token in state, and then sends it as a bearer authorization token header for every request made to the backend. The backend checks this access token for each api call, and only allows request to be made if they carry a valid authentication token. The user id is embedded in the access token so for every request made this is how the backend is able to determine the user id, by decoding it from access token.

We don’t want this access token to be valid for too long however as then if someone gets a hold of it they can sign in to the users account with this or call api routes. A more secure way is if the access token expired every 30 minutes and you had to keep creating new ones. This would however be quite annoying for the user as signing in every 30 minutes would become quite cumbersome. The solution for this is a refresh token.

### Refresh tokens

A refresh token is valid for longer than the access token (for this app 30 days) and essentially handles the relogging in every 30 minutes for you. Since it is valid for longer, it must be more secure, and hence is never sent over calls but rather stored as a httponly cookie. A cookie is a small piece of data that a website stores in your browser and automatically sends back with future requests to the site. It's kind of like a bookmark of certain information that stays when you log in from that browser. So the refresh token is created when a user logs in and is stored as a cookie. The refresh token is only needed when we need to refresh the access token, so the way it works is that if a route fails due to an expired access token, the code calls the refresh route which has credentials: ”include” so it sends the refresh token in the form of a cookie. And if the refresh token is valid, then it generated and sets the new access token, and then the failed route is retried. Only if the refresh route fails because the refresh token is expired do we need to relog in.

### Cross Site Request Forgery(CSRF) Protection

When using cookies, we also need to do some additional work to prevent Cross Site Request Forgery (CSRF) attacks. This is basically malicious javascript running on a different domain that tries to read our refresh token cookie. We deal with this threat through a method called double submit verification, the basic idea behind this being that a JWT coming from a cookie will only be considered valid if a special double submit token is also present in the request, and that double submit token must not be something that is automatically sent by a web browser (i.e it cannot be another cookie). Therefore, we include a double-submit token that is present as a header called “X-CSRF-TOKEN”. Refer to cookies section of [Flash-JWT-Extended docs](https://flask-jwt-extended.readthedocs.io/en/stable/token_locations.html) for more information. Note that when logging out we send a request to the logout route and send the access token to invalidate both the access and refresh token by adding them to a token blocklist.




## How JWT authentication is Implemented in App


### Backend Auth Implementation

On the backend, I used flask_jwt_extended to handle jwt authentication. The login route creates an access and refresh token, sending the access token back and storing the refresh token as a httponly cookie. THis is done through functions provided by flask-jwt-extended. The refresh route requires the refresh token and hence the csrf cookie, and just creates a new access token and returns it in the response alongside user username and email so the frontend can set auth. The logout route works by interacting with a TokenBlocklist table. This is a blocklist of all access and refresh tokens that should not be allowed to give access to routes. When logging out we want to add our current access and refresh token to this TokenBlocklist. The way tokens are checked against this before going to any route is that with flask-jwt-extended we can create a function of the form:

```
@jwt.token_in_blocklist_loader 
token_revoked(jwt_header, jwt_data);
```
 
In this function we define to return true if the token with jwt_data is in the blocklist and false if not, and flask_jwt_extended automatically runs this function and does this check whenever we call any route. 

### Logout user implementation

To logout, a user calls upon the logout route. The logout route gets the jti of the access token first. The jti is a unique identifier assigned to a unique token instance. The jti of the refresh token is taken from the claims of the access token, and this is possible because in the login route when the access token is created the jti of the refresh token is embedded in the claims of the access token. This simplifies things as we dont have to send the refresh token csrf cookie when calling the logout route. Then these two tokens are revoked by adding them to the tokenblocklist table. THey are additionally usnet using flask_jwt_extended function `unset_jwt_cookies(reponse)` where a successful response like “Logout successful” indicates they were unset. For more info refer to [flask-jwt-extended docs](https://flask-jwt-extended.readthedocs.io/en/stable/blocklist_and_token_revoking.html#revoking-refresh-tokens)


### Frontend Auth Implementation

On the frontend, I first created an AuthProvider file that uses CreateContext from react to provide auth throughout the entire frontend. The auth is just the username, email, and access token. This way we can access auth from any component by just doing 

`const {auth} = useContext(AuthContext);`

at the beginning. In order to setAuth, we create another file which is a hook called useAuth.js which just returns useContext(AuthContext) so that we can just do const {setAuth} = useAuth(); useAuth is a hook which is a special React function that lets function components use state, side effects, refs, and other React features without classes. There is also a file created called RequireAuth.js which uses Outlet and navigate to navigate to loginpage if auth is not set. This auth check wraps all the routes except for signuppage and logginpage. Signuppage and loginpage are just forms that send request to register and login routes. 

There also exists the functionality where if an api call fails due to an expired access token, the access token is refreshed the route is called again with the fresh access token. This was implemented on the frontend as so. In order to be able to do this, we need to make this so that any route we call with fetch, if it fails from being unathorized due to an expired access token, the refresh route is called and then this route is retried. The way I did this is by creating a custom wrapper around fetch called fetchWithAuth. A hook called useFetch.js was created and in this, I implemented the functionality where the original request is tried, and if it fails with a 401 error, then the refresh route is called, auth is updated, and original route is retried with new access token. All routes are then wrapped in this wrapper. The way fetch routes were wrapped in this is at the beginning of the component, writing `const fetchWithAuth = useFetch();` and just treating fetchWithAuth as a regular fetch.  
