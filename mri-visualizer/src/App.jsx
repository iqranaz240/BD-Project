import React from 'react'
import Header from './components/Header'
import Main from './components/Main'
import Footer from './components/Footer'
import HdfsImageViewer from './components/HdfsImageViewer'
import './App.css'

const App = () => {
  return (
    <div>

      <HdfsImageViewer />
      <Footer />
    </div>
  )
}

export default App
