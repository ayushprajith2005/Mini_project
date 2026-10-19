import { NavLink } from 'react-router-dom'
import { Icon } from './ui'

const main = [
  { to: '/', label: 'Predict', icon: 'pin', end: true },
  { to: '/log', label: 'Prediction log', icon: 'list' },
  { to: '/performance', label: 'Model performance', icon: 'chart' },
  { to: '/about', label: 'About', icon: 'info' },
]

export default function Sidebar() {
  return (
    <nav className="sidebar" aria-label="Main">
      <div className="brand">
        <svg width="26" height="26" viewBox="0 0 24 24" fill="none" stroke="#7cc4d8" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
          <path d="M12 3c3.5 4.2 6 7.2 6 10.5a6 6 0 0 1-12 0C6 10.2 8.5 7.2 12 3z" />
        </svg>
        RainXplain
      </div>
      <div className="nav">
        {main.map((item) => (
          <NavLink key={item.to} to={item.to} end={item.end}>
            <Icon name={item.icon} />
            {item.label}
          </NavLink>
        ))}
      </div>
      <div className="sidebar-foot">
        <div className="nav">
          <NavLink to="/admin" className="quiet">
            <Icon name="lock" />
            Admin
          </NavLink>
        </div>
        <div className="sidebar-note">XGBoost model, 406 stations.<br />Validated on 2024 to 2025 data.</div>
      </div>
    </nav>
  )
}
