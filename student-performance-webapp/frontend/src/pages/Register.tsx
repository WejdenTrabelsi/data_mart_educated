import { useState } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import axios from 'axios';

export default function Register() {
  const [form, setForm] = useState({
    username: '',
    email: '',
    password: '',
    full_name: '',
    student_natural_key: '',
    level_name: '',
    branch_name: '',
  });
  const [loading, setLoading] = useState(false);
  const [message, setMessage] = useState('');
  const navigate = useNavigate();

  const branchOptions: { [key: string]: string[] } = {
    "1ère année": ["General"],
    "2ème année": ["Science", "Eco"],
    "3ème année": ["Math", "Science", "Technique"],
    "4ème année (bac)": ["Math", "Science", "Technique"],
  };

  const handleChange = (e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement>) => {
    const { name, value } = e.target;
    setForm(prev => {
      const newForm = { ...prev, [name]: value };
      // Reset branch when level changes
      if (name === 'level_name') newForm.branch_name = '';
      return newForm;
    });
  };

  const handleRegister = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    try {
      await axios.post(`${import.meta.env.VITE_API_URL}/parent/register`, form);
      setMessage("✅ Demande envoyée ! En attente d'approbation du directeur.");
      setTimeout(() => navigate('/'), 3000);
    } catch (err: any) {
      setMessage('❌ ' + (err.response?.data?.detail || 'Erreur inconnue'));
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-[#F5F4FF] flex items-center justify-center p-4">
      <div className="max-w-md w-full bg-white rounded-3xl shadow-2xl p-8">
        <h1 className="text-3xl font-bold text-primary text-center">Inscription Parent</h1>
        <p className="text-center text-gray-500 mt-2 mb-8">Créez votre compte pour suivre les performances de votre enfant</p>
        
        <form onSubmit={handleRegister} className="space-y-5">
          <input name="full_name" placeholder="Votre nom complet" value={form.full_name} onChange={handleChange} required className="w-full px-4 py-3 border border-gray-300 rounded-2xl focus:outline-none focus:border-primary" />
          <input name="username" placeholder="Nom d'utilisateur" value={form.username} onChange={handleChange} required className="w-full px-4 py-3 border border-gray-300 rounded-2xl focus:outline-none focus:border-primary" />
          <input name="email" type="email" placeholder="Email" value={form.email} onChange={handleChange} required className="w-full px-4 py-3 border border-gray-300 rounded-2xl focus:outline-none focus:border-primary" />
          <input name="password" type="password" placeholder="Mot de passe" value={form.password} onChange={handleChange} required className="w-full px-4 py-3 border border-gray-300 rounded-2xl focus:outline-none focus:border-primary" />

          <select name="level_name" value={form.level_name} onChange={handleChange} required className="w-full px-4 py-3 border border-gray-300 rounded-2xl focus:outline-none focus:border-primary">
            <option value="">Sélectionner le niveau</option>
            <option value="1ère année">1ère année</option>
            <option value="2ème année">2ème année</option>
            <option value="3ème année">3ème année</option>
            <option value="4ème année (bac)">4ème année (bac)</option>
          </select>

          <select name="branch_name" value={form.branch_name} onChange={handleChange} required className="w-full px-4 py-3 border border-gray-300 rounded-2xl focus:outline-none focus:border-primary">
            <option value="">Sélectionner la branche</option>
            {form.level_name && branchOptions[form.level_name].map(b => (
              <option key={b} value={b}>{b}</option>
            ))}
          </select>

          <input name="student_natural_key" placeholder="Nom complet de l'enfant" value={form.student_natural_key} onChange={handleChange} required className="w-full px-4 py-3 border border-gray-300 rounded-2xl focus:outline-none focus:border-primary" />

          <button type="submit" disabled={loading} className="w-full bg-primary hover:bg-[#4338A0] text-white font-semibold py-4 rounded-2xl transition-all disabled:opacity-70">
            {loading ? 'Envoi en cours...' : "Envoyer la demande d'inscription"}
          </button>
        </form>

        {message && <p className="text-center mt-6 text-sm font-medium">{message}</p>}

        <p className="text-center mt-8 text-sm text-gray-500">
          Déjà un compte ? <Link to="/" className="text-primary font-semibold hover:underline">Se connecter</Link>
        </p>
      </div>
    </div>
  );
}