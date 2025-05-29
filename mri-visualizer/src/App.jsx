import React from 'react'
import { BrowserRouter as Router, Route, Routes, Link } from 'react-router-dom'
import Header from './components/Header'
import Main from './components/Main'
import Footer from './components/Footer'
import HdfsImageViewer from './components/HdfsImageViewer'
import Streaming from './components/Streaming'
import './App.css'

const App = () => {
  return (
    <div>
    <Router>
      <div>
      <Header />
      <div style={{marginTop: '-250px', alignItems: 'center', margin: '200px, 200px 100px auto', alignItems: 'center', alignSelf: 'center', textAlign: 'center', width: '100%'}}>
        <Routes>
          <Route path="/" element={<Main />} />
          <Route path="/hdfs" element={<HdfsImageViewer />} />
          <Route path="/streaming" element={<Streaming />} />
        </Routes>
        </div>
      </div>
    </Router>
    <Footer />
    </div>
  )
}

export default App
