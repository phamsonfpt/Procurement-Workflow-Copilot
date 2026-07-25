import React from 'react';
import { Routes, Route, Navigate } from 'react-router-dom';
import Login from './pages/Login';
import RequesterPage from './pages/Requester';
import ManagerPage from './pages/Manager';
import OpsPage from './pages/Ops';
import AdminPage from './pages/Admin';

export default function App() {
  return (
    <Routes>
      <Route path="/login" element={<Login />} />
      <Route path="/requester" element={<RequesterPage />} />
      <Route path="/manager" element={<ManagerPage />} />
      <Route path="/ops" element={<OpsPage />} />
      <Route path="/admin" element={<AdminPage />} />
      <Route path="*" element={<Navigate to="/login" replace />} />
    </Routes>
  );
}
