import './App.css';
import {HashRouter as Router, Routes, Route} from 'react-router-dom'
import { Home } from './Pages/homepage';
import { Stopwatch } from './Pages/stopwatchpage';
import { Habit } from './Pages/habitpage';
import { Layout } from './layout';

function App() {
  return (
    <Router>
      <Routes>
        <Route element = {<Layout/>}>
          <Route path="/" element = {<Home/>}/>
          <Route path="/habitpage" element = {<Habit/>}/>
          <Route path="/stopwatchpage" element = {<Stopwatch/>}/>
        </Route>
      </Routes>
    </Router>
  )
  
}

export default App;
