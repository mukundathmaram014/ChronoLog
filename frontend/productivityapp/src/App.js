import './App.css';
import {HashRouter as Router, Routes, Route} from 'react-router-dom'
import { Home } from './Pages/homepage';
import { Stopwatch } from './Pages/stopwatchpage';
import { Habit } from './Pages/habitpage';
import { Layout } from './layout';
import { Statistics } from './Pages/statisticspage';

function App() {
  return (
    <Router>
      <Routes>
        <Route element = {<Layout/>}>
          <Route path="/" element = {<Home/>}/>
          <Route path="/habitpage" element = {<Habit/>}/>
          <Route path="/stopwatchpage" element = {<Stopwatch/>}/>
          <Route path="/statisticspage" element = {<Statistics/>}/>
        </Route>
      </Routes>
    </Router>
  )
  
}

export default App;
