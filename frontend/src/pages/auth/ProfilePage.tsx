import React from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { useAuth } from '../../context/AuthContext';
import { User, Mail, Shield, LogOut, BookOpen, Clock, ArrowRight, CheckCircle2 } from 'lucide-react';

export const ProfilePage: React.FC = () => {
  const { user, logout, isAdmin } = useAuth();
  const navigate = useNavigate();

  const handleLogout = async () => {
    await logout();
    navigate('/login');
  };

  if (!user) {
    return null;
  }

  return (
    <div className="max-w-4xl mx-auto px-4 py-8 sm:px-6 lg:px-8">
      {/* Profile Header */}
      <div className="bg-white rounded-2xl shadow-sm border border-slate-200/80 p-6 sm:p-8 mb-8">
        <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-6">
          <div className="flex items-center space-x-5">
            <div className="w-16 h-16 rounded-2xl bg-gradient-to-tr from-indigo-600 to-indigo-500 text-white flex items-center justify-center text-2xl font-bold shadow-md shadow-indigo-100">
              {user.full_name ? user.full_name.charAt(0).toUpperCase() : user.email.charAt(0).toUpperCase()}
            </div>
            <div>
              <div className="flex items-center gap-3">
                <h1 className="text-2xl font-bold text-slate-900 tracking-tight">{user.full_name || 'Student'}</h1>
                <span
                  className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-semibold ${
                    isAdmin
                      ? 'bg-purple-100 text-purple-800 border border-purple-200'
                      : 'bg-emerald-100 text-emerald-800 border border-emerald-200'
                  }`}
                >
                  {isAdmin ? '🛡️ Administrator' : '🎓 Student'}
                </span>
              </div>
              <p className="text-sm text-slate-500 mt-1 flex items-center gap-1.5">
                <Mail className="w-4 h-4 text-slate-400" />
                {user.email}
              </p>
            </div>
          </div>

          <button
            onClick={handleLogout}
            className="inline-flex items-center px-4 py-2 border border-rose-200 rounded-xl text-sm font-medium text-rose-700 bg-rose-50 hover:bg-rose-100 transition-colors cursor-pointer"
          >
            <LogOut className="w-4 h-4 mr-2 text-rose-500" />
            Sign out
          </button>
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        {/* Account Details Card */}
        <div className="md:col-span-2 bg-white rounded-2xl shadow-sm border border-slate-200/80 p-6 sm:p-8">
          <h2 className="text-lg font-bold text-slate-900 mb-6 flex items-center gap-2">
            <User className="w-5 h-5 text-indigo-600" />
            Account Information
          </h2>

          <div className="space-y-4">
            <div className="flex flex-col sm:flex-row sm:items-center justify-between py-3 border-b border-slate-100">
              <span className="text-sm font-medium text-slate-500">Student ID</span>
              <span className="text-sm font-semibold text-slate-900 mt-1 sm:mt-0 font-mono">#{user.id}</span>
            </div>

            <div className="flex flex-col sm:flex-row sm:items-center justify-between py-3 border-b border-slate-100">
              <span className="text-sm font-medium text-slate-500">Full Name</span>
              <span className="text-sm font-semibold text-slate-900 mt-1 sm:mt-0">{user.full_name || 'Not provided'}</span>
            </div>

            <div className="flex flex-col sm:flex-row sm:items-center justify-between py-3 border-b border-slate-100">
              <span className="text-sm font-medium text-slate-500">Email Address</span>
              <span className="text-sm font-semibold text-slate-900 mt-1 sm:mt-0">{user.email}</span>
            </div>

            <div className="flex flex-col sm:flex-row sm:items-center justify-between py-3 border-b border-slate-100">
              <span className="text-sm font-medium text-slate-500">Mobile Phone</span>
              <span className="text-sm font-semibold text-slate-900 mt-1 sm:mt-0">
                {user.phone_number || 'None provided'}
              </span>
            </div>

            <div className="flex flex-col sm:flex-row sm:items-center justify-between py-3">
              <span className="text-sm font-medium text-slate-500">Account Status</span>
              <span className="inline-flex items-center text-xs font-semibold text-emerald-700 bg-emerald-50 px-2.5 py-1 rounded-md border border-emerald-100">
                <CheckCircle2 className="w-3.5 h-3.5 mr-1" />
                Active & Verified
              </span>
            </div>
          </div>
        </div>

        {/* Quick Shortcuts */}
        <div className="space-y-4">
          {!isAdmin ? (
            <>
              <Link
                to="/library"
                className="block p-5 bg-gradient-to-br from-indigo-50 to-white border border-indigo-100 rounded-2xl shadow-sm hover:shadow-md hover:border-indigo-200 transition-all group"
              >
                <div className="flex items-center justify-between">
                  <div className="w-10 h-10 rounded-xl bg-indigo-600 text-white flex items-center justify-center shadow-sm">
                    <BookOpen className="w-5 h-5" />
                  </div>
                  <ArrowRight className="w-5 h-5 text-slate-400 group-hover:text-indigo-600 group-hover:translate-x-1 transition-all" />
                </div>
                <h3 className="mt-4 font-bold text-slate-900">My Library</h3>
                <p className="text-xs text-slate-600 mt-1">Read your unlocked notes & monitor active class pass timers.</p>
              </Link>

              <Link
                to="/orders"
                className="block p-5 bg-gradient-to-br from-slate-50 to-white border border-slate-200 rounded-2xl shadow-sm hover:shadow-md hover:border-slate-300 transition-all group"
              >
                <div className="flex items-center justify-between">
                  <div className="w-10 h-10 rounded-xl bg-slate-800 text-white flex items-center justify-center shadow-sm">
                    <Clock className="w-5 h-5" />
                  </div>
                  <ArrowRight className="w-5 h-5 text-slate-400 group-hover:text-slate-800 group-hover:translate-x-1 transition-all" />
                </div>
                <h3 className="mt-4 font-bold text-slate-900">Order History</h3>
                <p className="text-xs text-slate-600 mt-1">View past transactions, payment IDs, and printable GST invoices.</p>
              </Link>
            </>
          ) : (
            <>
              <Link
                to="/admin/curriculum"
                className="block p-5 bg-gradient-to-br from-purple-50 to-white border border-purple-200 rounded-2xl shadow-sm hover:shadow-md hover:border-purple-300 transition-all group"
              >
                <div className="flex items-center justify-between">
                  <div className="w-10 h-10 rounded-xl bg-purple-700 text-white flex items-center justify-center shadow-sm">
                    <Shield className="w-5 h-5" />
                  </div>
                  <ArrowRight className="w-5 h-5 text-purple-400 group-hover:text-purple-700 group-hover:translate-x-1 transition-all" />
                </div>
                <h3 className="mt-4 font-bold text-purple-950">Curriculum Console</h3>
                <p className="text-xs text-purple-700/80 mt-1">Manage boards, classes, subjects, chapters & PDF uploads.</p>
              </Link>

              <Link
                to="/admin/products"
                className="block p-5 bg-gradient-to-br from-indigo-50 to-white border border-indigo-200 rounded-2xl shadow-sm hover:shadow-md hover:border-indigo-300 transition-all group"
              >
                <div className="flex items-center justify-between">
                  <div className="w-10 h-10 rounded-xl bg-indigo-700 text-white flex items-center justify-center shadow-sm">
                    <Shield className="w-5 h-5" />
                  </div>
                  <ArrowRight className="w-5 h-5 text-indigo-400 group-hover:text-indigo-700 group-hover:translate-x-1 transition-all" />
                </div>
                <h3 className="mt-4 font-bold text-indigo-950">Products & Pricing</h3>
                <p className="text-xs text-indigo-700/80 mt-1">Configure passes, subject packs, and commercial rates.</p>
              </Link>
            </>
          )}
        </div>
      </div>
    </div>
  );
};
