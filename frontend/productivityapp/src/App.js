import './App.css';
import {HashRouter as Router, Routes, Route} from 'react-router-dom'
import { Home } from './Pages/homepage';
import { Stopwatch } from './Pages/stopwatchpage';
import { Habit } from './Pages/habitpage';
import { Layout } from './layout';
import { Statistics } from './Pages/statisticspage';
import { LoginPage } from './Pages/loginpage';
import { SignupPage } from './Pages/signuppage';
import {useState} from "react";


function App() {

  const [isLoggedIn, setIsLoggedIn] = useState(!!localStorage.getItem("token"));
  console.log(isLoggedIn);

  return (
    <Router>
      <Routes>
        <Route path="/" element={<SignupPage />}/>
        <Route path= "/loginpage" element= {<LoginPage/>}/>
        <Route element = {<Layout/>}>
          <Route path="/homepage" element = {isLoggedIn ? <Home/> : <SignupPage />}/>
          <Route path="/habitpage" element = {isLoggedIn ? <Habit/> : <SignupPage />}/>
          <Route path="/stopwatchpage" element = {isLoggedIn ? <Stopwatch/> : <SignupPage />}/>
          <Route path="/statisticspage" element = {isLoggedIn ? <Statistics/> : <SignupPage />}/>
        </Route>
      </Routes>
    </Router>
  )
  
}

export default App;
