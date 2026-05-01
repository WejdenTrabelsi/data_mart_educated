// ---------------------------------------------------------------------------
// LOGIN.TSX  --  Authentication Page (React Functional Component)
// ---------------------------------------------------------------------------
// This is the first screen the Director sees. It collects username/password,
// sends them to the FastAPI backend, stores the returned JWT in localStorage,
// and redirects to the Dashboard on success.
// ---------------------------------------------------------------------------

// useState is the React Hook that lets functional components "remember" values
// between renders (like variables that survive re-painting).
// useNavigate is a React Router hook that programmatically changes the URL.
import { useState } from 'react';
import { useNavigate } from 'react-router-dom';

// Axios is an HTTP client. It sends POST/GET requests and handles JSON
// conversion automatically.
import axios from 'axios';

// LogIn is an icon component from the Lucide React icon library.
import { LogIn } from 'lucide-react';

// ---------------------------------------------------------------------------
// The component is exported as the default export so App.tsx can import it.
// ---------------------------------------------------------------------------
export default function Login() {
  
  // -------------------------------------------------------------------------
  // STATE HOOKS
  // -------------------------------------------------------------------------
  // useState('') creates a piece of state initialized to an empty string.
  // username holds the current value; setUsername updates it.
  // Every time setUsername is called, React re-renders the component.
  // -------------------------------------------------------------------------
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  
  // loading is true while we wait for the backend response.
  // It disables the button and changes its text to "Connexion...".
  const [loading, setLoading] = useState(false);
  
  // error stores the error message to display under the form.
  const [error, setError] = useState('');
  
  // navigate is a function. Calling navigate('/dashboard') changes the
  // browser URL instantly without a full page reload.
  const navigate = useNavigate();

  // -------------------------------------------------------------------------
  // handleLogin  --  The Form Submission Handler
  // -------------------------------------------------------------------------
  // async means this function can use "await" to pause for promises.
  // e is the browser's submit event object.
  // React.FormEvent is the TypeScript type for form submission events.
  // -------------------------------------------------------------------------
  const handleLogin = async (e: React.FormEvent) => {
    
    // Prevent the browser's default form submission, which would reload
    // the entire page. We want to handle this with JavaScript.
    e.preventDefault();
    
    // Reset UI states before starting the request.
    setLoading(true);
    setError('');

    try {
      // ---------------------------------------------------------------------
      // OAuth2 Password Flow requires the body to be URL-encoded,
      // NOT JSON. URLSearchParams builds that format:
      //   username=admin&password=admin123
      // ---------------------------------------------------------------------
      const formData = new URLSearchParams();
      formData.append('username', username);
      formData.append('password', password);

      // ---------------------------------------------------------------------
      // Axios POST request to the backend login endpoint.
      // import.meta.env.VITE_API_URL comes from the .env file (Vite exposes
      // only variables prefixed with VITE_ to the frontend).
      // The full URL becomes: http://127.0.0.1:8000/auth/login
      // ---------------------------------------------------------------------
      const res = await axios.post(`${import.meta.env.VITE_API_URL}/auth/login`, formData, {
        // We must explicitly tell the server this is form-encoded data.
        headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
      });

      // ---------------------------------------------------------------------
      // SUCCESS PATH
      // ---------------------------------------------------------------------
      // res.data contains the JSON body returned by FastAPI:
      // { access_token: "eyJ...", token_type: "bearer", full_name: "Administrateur" }
      // We persist these in localStorage so they survive page refreshes.
      // ---------------------------------------------------------------------
      localStorage.setItem('token', res.data.access_token);
      localStorage.setItem('full_name', res.data.full_name);

      // Redirect the user to the dashboard route.
      navigate('/dashboard');
    
    } catch (err: any) {
      // ---------------------------------------------------------------------
      // FAILURE PATH
      // ---------------------------------------------------------------------
      // If the server returns 401 or the network fails, axios throws.
      // We catch it and show a generic error message in French.
      // ---------------------------------------------------------------------
      setError('Identifiants incorrects');
    
    } finally {
      // finally runs whether the try succeeded or failed.
      // It re-enables the login button.
      setLoading(false);
    }
  };
  

  // -------------------------------------------------------------------------
  // JSX RETURN  --  The Visual Layout
  // -------------------------------------------------------------------------
  // className strings use Tailwind CSS utility classes.
  // min-h-screen = minimum height = full viewport height.
  // bg-[#F5F4FF] = custom lavender background color.
  // flex + items-center + justify-center = perfect centering.
  // -------------------------------------------------------------------------
  return (
    <div className="min-h-screen bg-[#F5F4FF] flex items-center justify-center p-4">
      {/* White card container with rounded corners and shadow */}
      <div className="max-w-md w-full bg-white rounded-3xl shadow-2xl p-8">
        
        {/* Icon centered at the top */}
        <div className="flex justify-center mb-6">
          <LogIn size={48} className="text-primary" />
        </div>
        
        {/* Title and subtitle */}
        <h1 className="text-4xl font-bold text-center text-primary mb-2">Bienvenue</h1>
        <p className="text-center text-gray-500 mb-8">Tableau de bord de performance scolaire</p>

        {/* The form element. onSubmit wires it to handleLogin. */}
        <form onSubmit={handleLogin} className="space-y-6">
          
          {/* Username input group */}
          <div>
            <label className="block text-sm font-medium mb-2">Nom d'utilisateur</label>
            <input
              type="text"
              value={username}
              // onChange fires every time the user types a character.
              // e.target.value is the new text in the input box.
              onChange={(e) => setUsername(e.target.value)}
              className="w-full px-4 py-3 border border-gray-300 rounded-2xl focus:outline-none focus:border-primary"
              placeholder="admin"
              required
            />
          </div>

          {/* Password input group */}
          <div>
            <label className="block text-sm font-medium mb-2">Mot de passe</label>
            <input
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              className="w-full px-4 py-3 border border-gray-300 rounded-2xl focus:outline-none focus:border-primary"
              placeholder="••••••••"
              required
            />
          </div>

          {/* Conditional error message. Only renders if error is not empty. */}
          {error && <p className="text-red-500 text-center text-sm">{error}</p>}

          {/* Submit button */}
          <button
            type="submit"
            disabled={loading}
            className="w-full bg-primary hover:bg-[#4338A0] text-white font-semibold py-4 rounded-2xl transition-all disabled:opacity-70"
          >
            
            
            {/* Ternary operator switches text based on loading state. */}
            {loading ? 'Connexion...' : 'Se connecter'}
          </button>
          

          

        </form>
      </div>
    </div>
  );
}