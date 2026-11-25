// src/App.jsx — Dueña: Paula. Todas las rutas ya están creadas: nadie necesita tocar este archivo.
import { BrowserRouter, Routes, Route, useLocation } from 'react-router-dom';
import { useEffect } from 'react';
import Navbar from './components/NavBar';
import Footer from './components/Footer';
import { SesionProvider } from './sesion/SesionContext';
import Inicio from './pages/Inicio/Inicio';
import Calendario from './pages/Calendario/Calendario';
import DetallesEvento from './pages/Evento/DetallesEvento';
import Tienda from './pages/Tienda/Tienda';
import Artista from './pages/Artista/Artista';
import Perfil from './perfiles/Perfil';

function ScrollToHash() {
  const location = useLocation();

  useEffect(() => {
    if (!location.hash) {
      window.scrollTo({ top: 0, behavior: 'smooth' });
      return;
    }
    const element = document.getElementById(location.hash.replace('#', ''));
    if (element) element.scrollIntoView({ behavior: 'smooth', block: 'start' });
  }, [location]);

  return null;
}

function App() {
  return (
    <SesionProvider>
      <BrowserRouter>
        <ScrollToHash />
        {/* El Navbar y Footer están fuera de las Routes para que se vean siempre */}
        <Navbar />
        <Routes>
          <Route path="/" element={<Inicio />} />                        {/* Paula (bloques: Pedro, Paula, Sergio) */}
          <Route path="/calendario" element={<Calendario />} />          {/* Pedro */}
          <Route path="/evento/:id" element={<DetallesEvento />} />      {/* Pedro (+ CartelEvento Sergio, ModalCheckout Luis) */}
          <Route path="/tienda" element={<Tienda />} />                  {/* Sergio */}
          <Route path="/artistas/:id" element={<Artista />} />           {/* Sergio */}
          <Route path="/perfil" element={<Perfil />} />                  {/* Paula (pestañas: todos) */}
        </Routes>
        <Footer />
      </BrowserRouter>
    </SesionProvider>
  );
}

export default App;
