import './App.css';
import { Routes, Route} from 'react-router-dom'
import { Home } from './Pages/homepage';
import { Stopwatch } from './Pages/stopwatchpage';
import { Habit } from './Pages/habitpage';
import { Layout } from './layout';
import { Statistics } from './Pages/statisticspage';
import { LoginPage } from './Pages/loginpage';
import { SignupPage } from './Pages/signuppage';
import {useContext} from "react";
import AuthContext from "./context/AuthProvider";
import RequireAuth from './Components/RequireAuth';


function App() {

  const { auth } = useContext(AuthContext);
  const isLoggedIn = !!auth?.access_token;
  console.log(isLoggedIn);

  return (
    <Routes>
      {/* Public routes - no layout/navbar */}
      <Route path="/" element={<SignupPage />}/>
      <Route path= "/loginpage" element= {<LoginPage/>}/>

      {/* Protected routes - with layout/navbar */}
      <Route element = {<RequireAuth/>}>
        <Route element={<Layout />}>
          <Route path="/homepage" element={<Home />}/>
          <Route path="/habitpage" element={<Habit />}/>
          <Route path="/stopwatchpage" element={<Stopwatch />}/>
          <Route path="/statisticspage" element={<Statistics />}/>
        </Route>
      </Route>
    </Routes>
  )
  
}

export default App;
