import React, { useState, useEffect } from 'react';
import { Calendar, ShieldCheck, AlertCircle, ArrowUpRight } from 'lucide-react';
import { Link } from 'react-router-dom';
import type { PassItem } from '../../types/library';

interface PassCountdownCardProps {
  pass: PassItem;
}

export const PassCountdownCard: React.FC<PassCountdownCardProps> = ({ pass }) => {
  const [timeLeft, setTimeLeft] = useState<{
    days: number;
    hours: number;
    minutes: number;
    seconds: number;
    isExpired: boolean;
  }>({
    days: pass.remaining_days,
    hours: 0,
    minutes: 0,
    seconds: 0,
    isExpired: !pass.is_active,
  });

  useEffect(() => {
    if (!pass.valid_until) return;

    const targetDate = new Date(pass.valid_until).getTime();

    const updateCountdown = () => {
      const now = new Date().getTime();
      const difference = targetDate - now;

      if (difference <= 0) {
        setTimeLeft({ days: 0, hours: 0, minutes: 0, seconds: 0, isExpired: true });
        return;
      }

      const days = Math.floor(difference / (1000 * 60 * 60 * 24));
      const hours = Math.floor((difference % (1000 * 60 * 60 * 24)) / (1000 * 60 * 60));
      const minutes = Math.floor((difference % (1000 * 60 * 60)) / (1000 * 60));
      const seconds = Math.floor((difference % (1000 * 60)) / 1000);

      setTimeLeft({ days, hours, minutes, seconds, isExpired: false });
    };

    updateCountdown();
    const interval = setInterval(updateCountdown, 1000);
    return () => clearInterval(interval);
  }, [pass.valid_until]);

  return (
    <div
      className={`rounded-3xl p-6 border transition-all ${
        timeLeft.isExpired
          ? 'bg-slate-50 border-slate-200 text-slate-500'
          : 'bg-gradient-to-br from-indigo-900 via-indigo-800 to-purple-900 text-white shadow-xl shadow-indigo-950/20'
      }`}
    >
      <div className="flex items-center justify-between mb-4">
        <span
          className={`px-3 py-1 text-xs font-black uppercase tracking-wider rounded-full ${
            timeLeft.isExpired
              ? 'bg-slate-200 text-slate-600'
              : 'bg-white/20 text-white backdrop-blur-md border border-white/20'
          }`}
        >
          {pass.board_name} • {pass.class_name} Pass
        </span>

        {timeLeft.isExpired ? (
          <span className="flex items-center text-xs font-bold text-rose-500 bg-rose-50 px-2.5 py-1 rounded-full border border-rose-200">
            <AlertCircle className="w-3.5 h-3.5 mr-1" /> Expired
          </span>
        ) : (
          <span className="flex items-center text-xs font-bold text-emerald-300 bg-emerald-500/20 px-2.5 py-1 rounded-full border border-emerald-400/30">
            <ShieldCheck className="w-3.5 h-3.5 mr-1" /> Active All-Access
          </span>
        )}
      </div>

      <h3 className={`text-xl font-black tracking-tight ${timeLeft.isExpired ? 'text-slate-800' : 'text-white'}`}>
        {pass.class_name} Full Curriculum Pass
      </h3>

      <p className={`text-xs mt-1 ${timeLeft.isExpired ? 'text-slate-400' : 'text-indigo-200'}`}>
        Unlocks all chapter notes, study guides, and subject packs across {pass.class_name}.
      </p>

      {/* Live Countdown Grid */}
      <div className="mt-5 grid grid-cols-4 gap-2 text-center">
        <div className={`p-2.5 rounded-2xl ${timeLeft.isExpired ? 'bg-slate-100' : 'bg-white/10 backdrop-blur-md'}`}>
          <span className={`text-xl font-black block ${timeLeft.isExpired ? 'text-slate-700' : 'text-white'}`}>
            {timeLeft.days}
          </span>
          <span className="text-[10px] font-bold uppercase tracking-wider opacity-75">Days</span>
        </div>
        <div className={`p-2.5 rounded-2xl ${timeLeft.isExpired ? 'bg-slate-100' : 'bg-white/10 backdrop-blur-md'}`}>
          <span className={`text-xl font-black block ${timeLeft.isExpired ? 'text-slate-700' : 'text-white'}`}>
            {timeLeft.hours}
          </span>
          <span className="text-[10px] font-bold uppercase tracking-wider opacity-75">Hours</span>
        </div>
        <div className={`p-2.5 rounded-2xl ${timeLeft.isExpired ? 'bg-slate-100' : 'bg-white/10 backdrop-blur-md'}`}>
          <span className={`text-xl font-black block ${timeLeft.isExpired ? 'text-slate-700' : 'text-white'}`}>
            {timeLeft.minutes}
          </span>
          <span className="text-[10px] font-bold uppercase tracking-wider opacity-75">Mins</span>
        </div>
        <div className={`p-2.5 rounded-2xl ${timeLeft.isExpired ? 'bg-slate-100' : 'bg-white/10 backdrop-blur-md'}`}>
          <span className={`text-xl font-black block ${timeLeft.isExpired ? 'text-slate-700' : 'text-white'}`}>
            {timeLeft.seconds}
          </span>
          <span className="text-[10px] font-bold uppercase tracking-wider opacity-75">Secs</span>
        </div>
      </div>

      {/* Validity details & renewal */}
      <div className="mt-5 pt-4 border-t border-white/10 flex items-center justify-between text-xs">
        <div className={`flex items-center space-x-1 ${timeLeft.isExpired ? 'text-slate-400' : 'text-indigo-200'}`}>
          <Calendar className="w-3.5 h-3.5" />
          <span>
            {pass.valid_until ? `Valid until ${new Date(pass.valid_until).toLocaleDateString()}` : 'Lifetime Access'}
          </span>
        </div>

        <Link
          to={`/products?class_id=${pass.class_id}&type=MONTHLY_PASS`}
          className={`font-bold inline-flex items-center hover:underline ${
            timeLeft.isExpired ? 'text-indigo-600' : 'text-amber-300'
          }`}
        >
          <span>Renew / Stack</span>
          <ArrowUpRight className="w-3.5 h-3.5 ml-0.5" />
        </Link>
      </div>
    </div>
  );
};
