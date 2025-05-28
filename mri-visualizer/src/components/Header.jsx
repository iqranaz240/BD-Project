import React from 'react';
import { Link } from 'react-router-dom';

const Header = () => {
    return (
        <header style={{ position: 'fixed', top: '10px', textAlign: 'center', width: '100%', alignItems: 'center', alignSelf: 'center'}}>
            <h1 style={{ color: 'white', fontSize: '2rem', fontWeight: 'bold', marginBottom: '100px', position: 'fixed', top: '10px', textAlign: 'center', width: '100%' }}>Stream Brain: MRI Tumor Analysis</h1>
            <nav style={{ position: 'fixed', top: '10px', width: '100%', marginTop: '50px'}}>
          <ul style={{ display: 'flex', listStyleType: 'none', justifyContent: 'center', alignItems: 'center', alignSelf: 'center'}}>
            <li style={{ margin: '0 15px' }}>
              <Link to="/">Local Processing</Link>
            </li>
            <li style={{ margin: '0 15px' }}>
              <Link to="/hdfs">HDFS Processing</Link>
            </li>
            <li style={{ margin: '0 15px' }}>
              <Link to="/streaming">Streaming</Link>
            </li>
          </ul>
        </nav>
        </header>
    );
};

export default Header;
