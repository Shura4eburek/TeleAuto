/**
 * TeleAuto — pywebview frontend
 */

import { useState, useEffect, useCallback, useRef, useContext } from 'react';
import { type Lang, type TrKey, tr as _tr, LangContext, UI } from './i18n';
import { Settings, Lock, Monitor, Activity, Terminal, Wifi, Eye, EyeOff, Info, X, Power } from 'lucide-react';
import { motion, AnimatePresence } from 'motion/react';

const FADE_MS = 160;

// ── Types ──────────────────────────────────────────────────────────────────
type View = 'loading' | 'config' | 'pin' | 'main' | 'shutdown';
type PanelState = 'off' | 'working' | 'connecting' | 'success' | 'error' | 'waiting';

interface Panel {
  state: PanelState;
  text: string;
}

function useTr() {
  const lang = useContext(LangContext);
  return (key: TrKey) => _tr(lang, key);
}

// ── pywebview API declaration ──────────────────────────────────────────────
declare global {
  interface Window {
    pywebview: {
      api: {
        get_initial_state(): Promise<{ view: View }>;
        save_config(
          login: string, password: string,
          pin: string, pinRepeat: string,
          startTelemart: boolean, telemartPath: string,
          language: string
        ): Promise<{ ok: boolean; view?: View; error?: string }>;
        verify_pin_input(pin: string): Promise<{ ok: boolean; error?: string }>;
        vpn_connect(): Promise<void>;
        vpn_disconnect(): Promise<void>;
        telemart_start(): Promise<void>;
        telemart_cancel(): Promise<void>;
        get_settings(pin: string): Promise<any>;
        save_settings(
          pin: string, login: string, password: string,
          secrets: Record<string, string>, startTelemart: boolean,
          telemartPath: string, language: string, manualOffset: number
        ): Promise<{ ok: boolean; error?: string }>;
        delete_credentials(): Promise<{ ok: boolean; error?: string }>;
        get_totp_preview(secret: string): Promise<{ ok: boolean; code: string }>;
        do_update(): Promise<{ ok: boolean }>;
        minimize(): Promise<void>;
        maximize(): Promise<void>;
        resize_window(width: number, height: number): Promise<void>;
        hide_to_tray(): Promise<void>;
        open_url(url: string): Promise<void>;
        quit(): Promise<void>;
      };
    };
    __update: (data: any) => void;
  }
}

// ── Helpers ────────────────────────────────────────────────────────────────
const STATE_COLOR: Record<PanelState, string> = {
  success:    '#34C759',
  error:      '#FF453A',
  working:    '#FF9F0A',
  connecting: '#FF9F0A',
  off:        'rgba(255,255,255,0.55)',
  waiting:    'rgba(255,255,255,0.55)',
};

function ts() {
  return new Date().toLocaleTimeString('uk-UA', {
    hour: '2-digit', minute: '2-digit', second: '2-digit',
  });
}

function api() { return window.pywebview?.api; }

// ── Input component ────────────────────────────────────────────────────────
function Input({
  value, onChange, type = 'text', placeholder = '', disabled = false, autoFocus = false,
  onEnter,
}: {
  value: string; onChange: (v: string) => void;
  type?: string; placeholder?: string; disabled?: boolean; autoFocus?: boolean;
  onEnter?: () => void;
}) {
  return (
    <input
      type={type}
      value={value}
      onChange={e => onChange(e.target.value)}
      placeholder={placeholder}
      disabled={disabled}
      autoFocus={autoFocus}
      onKeyDown={e => e.key === 'Enter' && onEnter?.()}
      onMouseDown={e => e.stopPropagation()}
      className="w-full bg-white/[0.08] border border-white/[0.12] rounded-[8px] px-3 py-2 text-white text-sm outline-none focus:border-[#0A84FF] disabled:opacity-40 transition-colors"
    />
  );
}

// ── Traffic lights ─────────────────────────────────────────────────────────
function TrafficLights({
  onClose, onMinimize, onMaximize,
}: {
  onClose: () => void; onMinimize?: () => void; onMaximize?: () => void;
}) {
  return (
    <div className="flex gap-2">
      <button
        onClick={onClose}
        className="w-3 h-3 rounded-full bg-[#FF5F56] border border-[#E0443E]/50 hover:brightness-110 transition-all"
      />
      <button
        onClick={onMinimize}
        className="w-3 h-3 rounded-full bg-[#FFBD2E] border border-[#DEA123]/50 hover:brightness-110 transition-all"
      />
      <button
        onClick={onMaximize}
        className="w-3 h-3 rounded-full bg-[#27C93F] border border-[#1AAB29]/50 hover:brightness-110 transition-all"
      />
    </div>
  );
}

// ── Config View ────────────────────────────────────────────────────────────
function ConfigView({ onDone }: { onDone: (view: View) => void }) {
  const t = useTr();
  const lang = useContext(LangContext);
  const [login, setLogin] = useState('');
  const [password, setPassword] = useState('');
  const [pin, setPin] = useState('');
  const [pinRepeat, setPinRepeat] = useState('');
  const [startTelemart, setStartTelemart] = useState(false);
  const [telemartPath, setTelemartPath] = useState('');
  const [language, setLanguage] = useState(lang);
  const [showPass, setShowPass] = useState(false);
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  const handleSave = async () => {
    if (!pin) { setError(t('error_pin_required')); return; }
    if (pin.length < 4) { setError(t('error_pin_short')); return; }
    if (pin !== pinRepeat) { setError(t('error_pin_mismatch')); return; }
    setLoading(true);
    setError('');
    const result = await api().save_config(
      login, password, pin, pinRepeat, startTelemart, telemartPath, language
    );
    setLoading(false);
    if (result.ok) {
      onDone(result.view as View);
    } else {
      setError(result.error ?? t('error_generic'));
    }
  };

  const inputCls = 'w-full bg-black/20 border border-white/10 rounded-lg px-3 py-2 text-[13px] focus:outline-none focus:bg-black/30 focus:border-white/30 transition-all text-white placeholder:text-white/30 shadow-inner';

  return (
    <div className="h-screen flex flex-col border border-white/[0.08]">
      <header className="h-[52px] flex items-center px-4 border-b border-white/[0.08] select-none pywebview-drag-region shrink-0">
        <TrafficLights onClose={() => api().quit()} onMinimize={() => api().minimize()} onMaximize={() => api().maximize()} />
        <div className="flex-1 text-center text-white/90 text-[13px] font-semibold">{t('config_title')}</div>
      </header>

      <div className="flex-1 overflow-y-auto p-5 flex flex-col gap-4 pb-24">

        {/* Telemart */}
        <div className="bg-white/[0.06] rounded-[10px] border border-white/[0.08] p-4 flex flex-col gap-3">
          <div className="flex items-center gap-2">
            <Monitor size={13} className="text-[#5E5CE6]" />
            <span className="text-[12px] font-medium text-white/70">Telemart</span>
          </div>
          <input autoFocus type="text" placeholder={t('login_ph')} value={login} onChange={e => setLogin(e.target.value)} onMouseDown={e => e.stopPropagation()} className={inputCls} />
          <div className="relative">
            <input type={showPass ? 'text' : 'password'} placeholder={t('pass_ph')} value={password} onChange={e => setPassword(e.target.value)} onMouseDown={e => e.stopPropagation()} className={inputCls + ' pr-9'} />
            <button onClick={() => setShowPass(v => !v)} className="absolute right-2.5 top-1/2 -translate-y-1/2 text-white/40 hover:text-white/70 transition-colors">
              {showPass ? <EyeOff size={14} /> : <Eye size={14} />}
            </button>
          </div>
        </div>

        {/* PIN */}
        <div className="bg-white/[0.06] rounded-[10px] border border-white/[0.08] p-4 flex flex-col gap-3">
          <div className="flex items-center gap-2">
            <Lock size={13} className="text-[#0A84FF]" />
            <span className="text-[12px] font-medium text-white/70">{t('pin_section')} <span className="text-white/30 font-normal">{t('optional')}</span></span>
          </div>
          <input type="password" placeholder={t('pin_ph')} value={pin} onChange={e => setPin(e.target.value)} onMouseDown={e => e.stopPropagation()} className={inputCls + ' tracking-widest'} />
          <input type="password" placeholder={t('pin_repeat_ph')} value={pinRepeat} onChange={e => setPinRepeat(e.target.value)} onMouseDown={e => e.stopPropagation()} className={inputCls + ' tracking-widest'} />
        </div>

        {/* Telemart */}
        <div className="bg-white/[0.06] rounded-[10px] border border-white/[0.08] p-4 flex flex-col gap-3">
          <div className="flex items-center gap-2">
            <Monitor size={13} className="text-[#5E5CE6]" />
            <span className="text-[12px] font-medium text-white/70">Telemart</span>
          </div>
          <label className="flex items-center gap-2 cursor-pointer select-none" onMouseDown={e => e.stopPropagation()}>
            <input type="checkbox" checked={startTelemart} onChange={e => setStartTelemart(e.target.checked)} className="accent-[#0A84FF] w-4 h-4" />
            <span className="text-[13px] text-white/80">{t('auto_start')}</span>
          </label>
          {startTelemart && (
            <input type="text" placeholder={t('tm_path_ph')} value={telemartPath} onChange={e => setTelemartPath(e.target.value)} onMouseDown={e => e.stopPropagation()} className={inputCls} />
          )}
        </div>

        {/* Language */}
        <div className="flex gap-2">
          {(['ua','ru','en'] as const).map(l => (
            <button key={l} onClick={() => setLanguage(l)}
              className={`flex-1 py-1.5 rounded-lg text-[12px] font-medium border transition-colors
                ${language === l ? 'bg-[#0A84FF]/20 border-[#0A84FF]/40 text-[#0A84FF]' : 'bg-white/5 border-white/10 text-white/50 hover:text-white/70'}`}>
              {l.toUpperCase()}
            </button>
          ))}
        </div>

        {/* Info */}
        <div className="bg-[#0A84FF]/10 border border-[#0A84FF]/30 rounded-[10px] p-3.5 flex items-start gap-3">
          <Info size={15} className="text-[#0A84FF] shrink-0 mt-0.5" />
          <p className="text-[11px] text-[#0A84FF] leading-relaxed">{t('vpn_info')}</p>
        </div>
      </div>

      <div className="absolute bottom-0 left-0 right-0 p-4 bg-white/[0.02] backdrop-blur-md border-t border-white/[0.08] flex flex-col gap-2">
        {error && <p className="text-[#FF453A] text-[12px]">{error}</p>}
        <button
          disabled={loading}
          onClick={handleSave}
          className="w-full bg-[#0A84FF] hover:bg-[#007AFF] disabled:opacity-50 text-white text-[13px] font-medium py-2.5 rounded-lg transition-colors shadow-[inset_0_1px_0_rgba(255,255,255,0.2),0_1px_2px_rgba(0,0,0,0.2)] border border-[#0A84FF]"
        >
          {loading ? t('saving') : t('save_config_btn')}
        </button>
      </div>
    </div>
  );
}

// ── PIN View ───────────────────────────────────────────────────────────────
function PinView({ onDone }: { onDone: (pin: string, startTelemart: boolean, language?: string) => void }) {
  const t = useTr();
  const [pin, setPin] = useState('');
  const [shake, setShake] = useState(false);
  const [loading, setLoading] = useState(false);

  const shakeTimer = useRef<ReturnType<typeof setTimeout> | null>(null);
  useEffect(() => () => { if (shakeTimer.current) clearTimeout(shakeTimer.current); }, []);

  const handleUnlock = async () => {
    if (!pin) return;
    setLoading(true);
    const result = await api().verify_pin_input(pin);
    setLoading(false);
    if (result.ok) {
      onDone(pin, result.start_telemart ?? true, result.language);
    } else {
      setShake(true);
      setPin('');
      shakeTimer.current = setTimeout(() => setShake(false), 500);
    }
  };

  return (
    <div className="h-screen flex flex-col border border-white/[0.08]">
      <header className="h-[52px] flex items-center px-4 border-b border-white/[0.08] select-none pywebview-drag-region shrink-0">
        <TrafficLights onClose={() => api().quit()} onMinimize={() => api().minimize()} onMaximize={() => api().maximize()} />
        <div className="flex-1 text-center text-white/90 text-[13px] font-semibold">TeleAuto</div>
      </header>

      <div className="flex-1 flex flex-col items-center justify-center p-8 pb-16 gap-6">
        <div className="w-20 h-20 rounded-full bg-[#0A84FF]/10 flex items-center justify-center shadow-[0_0_40px_rgba(10,132,255,0.2)] border border-[#0A84FF]/20">
          <Lock size={32} className="text-[#0A84FF]" strokeWidth={1.5} />
        </div>
        <input
          type="password"
          value={pin}
          onChange={e => setPin(e.target.value)}
          onKeyDown={e => e.key === 'Enter' && handleUnlock()}
          onMouseDown={e => e.stopPropagation()}
          autoFocus
          maxLength={8}
          className={`w-full max-w-[240px] h-[46px] bg-white/10 border rounded-full text-center text-[15px] tracking-[0.4em] focus:outline-none focus:bg-white/15 transition-all text-white placeholder:text-white/40 placeholder:tracking-normal shadow-inner backdrop-blur-md
            ${shake ? 'border-[#FF453A] animate-[shake_0.4s_ease-in-out]' : 'border-white/20 focus:border-white/40'}`}
          placeholder={t('pin_enter')}
        />
        <button
          disabled={loading || !pin}
          onClick={handleUnlock}
          className="w-full max-w-[240px] bg-[#0A84FF] hover:bg-[#007AFF] disabled:opacity-50 text-white text-[13px] font-medium py-2.5 rounded-full transition-colors shadow-[inset_0_1px_0_rgba(255,255,255,0.2),0_2px_8px_rgba(10,132,255,0.3)] border border-[#0A84FF]"
        >
          {loading ? t('checking') : t('unlock_btn')}
        </button>
      </div>
    </div>
  );
}

// ── TOTP preview field ────────────────────────────────────────────────────
function TotpField({ name, value, onChange }: {
  name: string; value: string; onChange: (v: string) => void;
}) {
  const [code, setCode] = useState('');

  useEffect(() => {
    if (!value || value.trim().length < 16) { setCode(''); return; }
    let cancelled = false;
    const refresh = async () => {
      const res = await api()?.get_totp_preview(value.trim());
      if (!cancelled && res?.ok) setCode(res.code);
      else if (!cancelled) setCode('');
    };
    refresh();
    const id = setInterval(refresh, 10000);
    return () => { cancelled = true; clearInterval(id); };
  }, [value]);

  return (
    <div className="flex gap-2 items-center">
      <span className="text-white/70 text-sm w-28 shrink-0 truncate" title={name}>{name}</span>
      <div className="flex-1">
        <Input value={value} onChange={onChange} type="password" />
      </div>
      {code && (
        <span className="text-[#34C759] font-mono text-sm w-16 text-right shrink-0 tabular-nums">{code}</span>
      )}
    </div>
  );
}

// ── Settings Modal ─────────────────────────────────────────────────────────
function SettingsModal({
  onClose, hasPin, userPin, onSaved, onPinChanged,
}: {
  onClose: () => void; hasPin: boolean; userPin: string;
  onSaved: (startTelemart: boolean, language: string) => void;
  onPinChanged?: (newPin: string) => void;
}) {
  const t = useTr();
  const [tab, setTab] = useState<'accounts' | 'security' | 'language'>('accounts');
  const [pin] = useState(hasPin ? userPin : '');
  const [newPin, setNewPin] = useState('');
  const [newPinRepeat, setNewPinRepeat] = useState('');
  const [pinError, setPinError] = useState('');
  const [pinSaved, setPinSaved] = useState(false);
  const pinSavedTimer = useRef<ReturnType<typeof setTimeout> | null>(null);
  const [data, setData] = useState<any>(null);
  const [error, setError] = useState('');
  const [saving, setSaving] = useState(false);
  const [saveMsg, setSaveMsg] = useState('');

  const saveMsgTimer = useRef<ReturnType<typeof setTimeout> | null>(null);
  useEffect(() => {
    let cancelled = false;
    api().get_settings(pin).then((res: any) => {
      if (cancelled) return;
      if (res.ok) setData(res);
      else setError(res.error);
    });
    return () => {
      cancelled = true;
      if (saveMsgTimer.current) clearTimeout(saveMsgTimer.current);
      if (pinSavedTimer.current) clearTimeout(pinSavedTimer.current);
    };
  }, []);

  const handleSave = async () => {
    if (!data) return;
    setSaving(true);
    const result = await api().save_settings(
      pin, data.login, data.password,
      data.secrets, data.start_telemart,
      data.telemart_path, data.language, data.manual_offset,
    );
    setSaving(false);
    if (result.ok) {
      setSaveMsg(t('saved_msg'));
      saveMsgTimer.current = setTimeout(() => setSaveMsg(''), 2000);
      onSaved(data.start_telemart, data.language);
    } else {
      setError(result.error ?? 'Помилка');
    }
  };

  const handlePinChange = async () => {
    setPinError('');
    if (!newPin) { setPinError(t('error_pin_required')); return; }
    if (newPin.length < 4) { setPinError(t('error_pin_short')); return; }
    if (newPin !== newPinRepeat) { setPinError(t('error_pin_mismatch')); return; }
    if (!data) return;
    setSaving(true);
    const result = await api().save_settings(
      newPin, data.login, data.password,
      data.secrets, data.start_telemart,
      data.telemart_path, data.language, data.manual_offset,
    );
    setSaving(false);
    if (result.ok) {
      setNewPin('');
      setNewPinRepeat('');
      setPinSaved(true);
      pinSavedTimer.current = setTimeout(() => setPinSaved(false), 2000);
      onPinChanged?.(newPin);
    } else {
      setPinError(result.error ?? t('error_generic'));
    }
  };

  const handleDelete = async () => {
    if (!confirm(t('delete_confirm'))) return;
    await api().delete_credentials();
    api().quit();
  };

  const inputCls = 'w-full bg-black/20 border border-white/10 rounded-lg px-3 py-2.5 text-sm focus:outline-none focus:border-[#0A84FF] transition-colors shadow-inner text-white placeholder:text-white/30';
  const tabBtn = (t: typeof tab, label: string) => (
    <button onClick={() => setTab(t)}
      className={`text-left px-3 py-2 rounded-lg text-sm font-medium transition-colors ${tab === t ? 'bg-white/10 text-white shadow-sm' : 'text-white/60 hover:bg-white/5 hover:text-white'}`}>
      {label}
    </button>
  );

  return (
    <AnimatePresence>
      <motion.div
        initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}
        transition={{ duration: 0.2 }}
        className="absolute inset-0 z-50 bg-black/40 backdrop-blur-sm flex items-center justify-center p-4"
      >
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={{ opacity: 0 }}
          transition={{ duration: 0.18 }}
          className="w-full max-w-[520px] h-[420px] bg-[#1E1E1E]/90 backdrop-blur-2xl rounded-[12px] shadow-[0_30px_60px_-12px_rgba(0,0,0,0.6),0_0_0_1px_rgba(255,255,255,0.1)_inset] border border-white/20 flex overflow-hidden flex-col"
        >
          {/* Header */}
          <div className="h-12 border-b border-white/10 flex items-center justify-between px-4 shrink-0 bg-white/[0.02]">
            <h3 className="font-semibold text-white/90 text-[13px]">{t('settings_title')}</h3>
            <button onClick={onClose} className="text-white/50 hover:text-white bg-white/5 hover:bg-white/10 rounded-full p-1.5 transition-colors">
              <X size={14} />
            </button>
          </div>

          <div className="flex-1 flex overflow-hidden">
            {/* Sidebar */}
            <div className="w-[140px] border-r border-white/10 bg-white/[0.02] p-3 flex flex-col gap-1">
              {tabBtn('accounts', t('tab_accounts'))}
              {tabBtn('security', t('tab_security'))}
              {tabBtn('language', t('tab_lang'))}
            </div>

            {/* Content */}
            <div className="flex-1 p-5 overflow-y-auto flex flex-col">
              {error && <p className="text-[#FF453A] text-xs mb-3">{error}</p>}
              {!data ? (
                <p className="text-white/40 text-sm text-center m-auto">{t('checking')}...</p>
              ) : (
                <>
                  {tab === 'accounts' && (
                    <div className="flex flex-col gap-4">
                      <div className="flex flex-col gap-2">
                        <h4 className="text-[11px] font-medium text-white/50 uppercase tracking-wider">Telemart</h4>
                        <input type="text" value={data.login} onChange={e => setData({...data, login: e.target.value})} onMouseDown={e => e.stopPropagation()} placeholder={t('login_ph')} className={inputCls} />
                        <input type="password" value={data.password} onChange={e => setData({...data, password: e.target.value})} onMouseDown={e => e.stopPropagation()} placeholder={t('pass_ph')} className={inputCls} />
                        {data.profiles.length > 0 && (
                          <div className="flex flex-col gap-2 mt-1">
                            <span className="text-[11px] text-white/40">{t('vpn_secrets')}</span>
                            {data.profiles.map((p: string) => (
                              <TotpField key={p} name={p} value={data.secrets[p] ?? ''}
                                onChange={v => setData({...data, secrets: {...data.secrets, [p]: v}})} />
                            ))}
                          </div>
                        )}
                      </div>
                      <div className="flex flex-col gap-2">
                        <h4 className="text-[11px] font-medium text-white/50 uppercase tracking-wider">{t('telemart_launch')}</h4>
                        <label className="flex items-center gap-2 cursor-pointer select-none" onMouseDown={e => e.stopPropagation()}>
                          <input type="checkbox" checked={data.start_telemart} onChange={e => setData({...data, start_telemart: e.target.checked})} className="accent-[#0A84FF] w-4 h-4" />
                          <span className="text-sm text-white/80">{t('auto_start_short')}</span>
                        </label>
                        {data.start_telemart && (
                          <input type="text" value={data.telemart_path} onChange={e => setData({...data, telemart_path: e.target.value})} onMouseDown={e => e.stopPropagation()} placeholder={t('tm_path_ph')} className={inputCls} />
                        )}
                        <div className="flex items-center gap-3 mt-1">
                          <span className="text-[11px] text-white/40 shrink-0">{t('totp_offset')}</span>
                          <input type="number" value={data.manual_offset} onChange={e => setData({...data, manual_offset: parseInt(e.target.value)||0})} onMouseDown={e => e.stopPropagation()}
                            className="w-20 bg-black/20 border border-white/10 rounded-lg px-2 py-1.5 text-sm text-white focus:outline-none focus:border-[#0A84FF]" />
                        </div>
                      </div>
                    </div>
                  )}

                  {tab === 'security' && (
                    <div className="flex flex-col gap-3">
                      <h4 className="text-[11px] font-medium text-white/50 uppercase tracking-wider">{t('change_pin')}</h4>
                      <input type="password" value={newPin} onChange={e => setNewPin(e.target.value)} placeholder={t('new_pin_ph')} onMouseDown={e => e.stopPropagation()} className={inputCls + ' tracking-widest'} />
                      <input type="password" value={newPinRepeat} onChange={e => setNewPinRepeat(e.target.value)} placeholder={t('repeat_pin_ph')} onMouseDown={e => e.stopPropagation()} onKeyDown={e => e.key === 'Enter' && handlePinChange()} className={inputCls + ' tracking-widest'} />
                      {pinError && <p className="text-[#FF453A] text-xs">{pinError}</p>}
                      {pinSaved && <p className="text-[#34C759] text-xs">{t('saved_msg')}</p>}
                      <button onClick={handlePinChange} disabled={saving} className="mt-1 bg-white/10 hover:bg-white/15 disabled:opacity-50 text-white text-sm font-medium py-2.5 rounded-lg transition-colors border border-white/5">
                        {saving ? t('checking') : t('update_pin_btn')}
                      </button>
                    </div>
                  )}

                  {tab === 'language' && (
                    <div className="flex flex-col gap-2">
                      <h4 className="text-[11px] font-medium text-white/50 uppercase tracking-wider mb-1">{t('select_lang')}</h4>
                      {([['ua','Українська (UA)'],['en','English (EN)'],['ru','Русский (RU)']] as const).map(([code, label]) => (
                        <label key={code} onMouseDown={e => e.stopPropagation()}
                          className="flex items-center gap-3 p-3 rounded-xl bg-white/5 border border-white/10 cursor-pointer hover:bg-white/10 transition-colors">
                          <input type="radio" name="lang" checked={data.language === code} onChange={() => setData({...data, language: code})} className="accent-[#0A84FF] w-4 h-4" />
                          <span className="text-sm font-medium">{label}</span>
                        </label>
                      ))}
                    </div>
                  )}

                  {/* Danger zone (all tabs) */}
                  <div className="mt-auto pt-5 border-t border-white/10">
                    <p className="text-[10px] font-bold text-[#FF453A] uppercase tracking-wider mb-2">{t('danger_zone')}</p>
                    <button onClick={handleDelete}
                      className="w-full bg-[#FF453A]/10 hover:bg-[#FF453A]/20 text-[#FF453A] border border-[#FF453A]/30 text-sm font-medium py-2 rounded-lg transition-colors">
                      {t('delete_all_btn')}
                    </button>
                  </div>
                </>
              )}
            </div>
          </div>

          {/* Footer */}
          {data && (
            <div className="h-12 border-t border-white/10 flex items-center justify-end gap-3 px-4 shrink-0 bg-white/[0.02]">
              {saveMsg && <span className="text-[#34C759] text-xs mr-auto">{saveMsg}</span>}
              <button onClick={onClose} className="text-white/50 hover:text-white text-sm transition-colors">{t('cancel')}</button>
              <button disabled={saving} onClick={handleSave}
                className="px-4 py-1.5 bg-[#0A84FF] hover:bg-[#007AFF] disabled:opacity-50 text-white text-sm font-medium rounded-lg transition-colors">
                {saving ? t('saving') : t('save_btn')}
              </button>
            </div>
          )}
        </motion.div>
      </motion.div>
    </AnimatePresence>
  );
}

// ── Shutdown View ─────────────────────────────────────────────────────────
function ShutdownView() {
  const t = useTr();
  return (
    <div className="h-screen bg-[#1E1E1E] flex flex-col items-center justify-center border border-white/[0.12]">
      <div className="flex flex-col items-center gap-6">
        <div className="w-16 h-16 rounded-full bg-white/5 flex items-center justify-center border border-white/10 shadow-inner">
          <Power size={28} className="text-white/50 animate-pulse" strokeWidth={1.5} />
        </div>
        <span className="text-[13px] font-medium text-white/50 tracking-wide">{t('shutting_down')}</span>
      </div>
      <div className="absolute bottom-12 left-1/2 -translate-x-1/2 w-48 h-1 bg-white/10 rounded-full overflow-hidden">
        <motion.div
          className="h-full bg-white/40 rounded-full"
          initial={{ width: '0%' }}
          animate={{ width: '100%' }}
          transition={{ duration: 4, ease: 'easeInOut' }}
        />
      </div>
    </div>
  );
}

// ── Main View ──────────────────────────────────────────────────────────────
function MainView({
  pritunl, telemart, monitor,
  net, vpnConnected, isBusy, updateTag,
  logs, logRef, userPin, version, startTelemart, profileStatuses, onOpenConfig, onStartTelematChange, onLangChange, onPinChanged,
}: {
  pritunl: Panel; telemart: Panel; monitor: Panel;
  net: { connected: boolean; ping: number | null };
  vpnConnected: boolean; isBusy: boolean; updateTag: string | null;
  logs: string[]; logRef: React.RefObject<HTMLDivElement | null>;
  userPin: string; version: string; startTelemart: boolean; profileStatuses: Record<string, string>; onOpenConfig?: () => void; onStartTelematChange?: (v: boolean) => void; onLangChange?: (v: string) => void; onPinChanged?: (p: string) => void;
}) {
  const t = useTr();
  const [showSettings, setShowSettings] = useState(false);
  const hasPin = !!userPin;

  return (
    <div className="h-screen w-full font-sans text-white flex flex-col overflow-hidden border border-white/[0.08]">
      <div className="h-full flex flex-col">
        {/* Header — drag region */}
        <header className="h-[52px] flex items-center px-4 relative shrink-0 select-none pywebview-drag-region">
          <div className="flex gap-2 absolute left-4 z-20">
            <TrafficLights
              onClose={() => api().hide_to_tray()}
              onMinimize={() => api().minimize()}
              onMaximize={() => api().maximize()}
            />
          </div>

          <div className="flex-1 flex justify-center items-center gap-2 absolute inset-0 pointer-events-none">
            <span className="text-white/90 text-[13px] font-semibold tracking-wide">TeleAuto</span>
            <button
              onClick={() => api().open_url('https://github.com/Shura4eburek/TeleAuto')}
              className="bg-white/10 text-white/70 text-[10px] px-1.5 py-0.5 rounded font-medium border border-white/5 hover:bg-white/20 hover:text-white transition-colors cursor-pointer"
            >{version || 'v1.3'}</button>
          </div>

          <div className="absolute right-4 flex items-center gap-3 z-20">
            {updateTag ? (
              <button
                onClick={() => api().do_update()}
                className="text-[11px] text-[#34C759] bg-[#34C759]/10 border border-[#34C759]/30 rounded-[10px] px-2 py-0.5 hover:bg-[#34C759]/20 transition-colors"
              >
                ↑ {updateTag}
              </button>
            ) : (
              <div className="w-2 h-2 rounded-full bg-[#34C759] shadow-[0_0_8px_rgba(52,199,89,0.5)]" />
            )}
            <button
              className="text-white/70 hover:text-white transition-colors"
              onClick={() => setShowSettings(true)}
            >
              <Settings size={15} />
            </button>
          </div>
        </header>

        {/* Content */}
        <main className="flex-1 overflow-y-auto p-5 flex flex-col gap-5">
          {/* Service cards */}
          <div className="bg-white/[0.06] rounded-[10px] border border-white/[0.08] overflow-hidden shadow-sm">
            {/* Pritunl row */}
            <div className="flex items-center px-4 py-3 justify-between border-b border-white/[0.06] hover:bg-white/[0.02] transition-colors">
              <div className="flex items-center gap-3">
                <div className="w-8 h-8 rounded-[8px] bg-gradient-to-b from-[#34C759] to-[#28A745] flex items-center justify-center shadow-sm border border-white/20">
                  <Lock size={16} strokeWidth={2.5} />
                </div>
                <div className="flex flex-col">
                  <span className="font-medium text-[14px] text-white leading-tight">Pritunl VPN</span>
                  <span className="text-[12px] mt-0.5 transition-colors" style={{ color: STATE_COLOR[pritunl.state] }}>
                    {pritunl.text || t('status_waiting')}
                  </span>
                </div>
              </div>
              {pritunl.state === 'working' || pritunl.state === 'connecting' ? (
                <button
                  onClick={() => api().vpn_disconnect()}
                  className="text-[12px] font-medium px-3 py-1 rounded-[6px] border transition-colors bg-[#FF453A]/15 hover:bg-[#FF453A]/25 text-[#FF453A] border-[#FF453A]/30"
                >
                  {t('cancel')}
                </button>
              ) : vpnConnected ? (
                <button
                  onClick={() => api().vpn_disconnect()}
                  className="text-[12px] font-medium px-3 py-1 rounded-[6px] border transition-colors bg-white/10 hover:bg-white/20 text-white border-white/10"
                >
                  {t('disconnect')}
                </button>
              ) : (
                <button
                  onClick={() => api().vpn_connect()}
                  disabled={isBusy}
                  className="text-[12px] font-medium px-3 py-1 rounded-[6px] border transition-colors bg-[#0A84FF] hover:bg-[#007AFF] disabled:opacity-50 text-white border-[#0A84FF]"
                >
                  {t('connect')}
                </button>
              )}
            </div>

            {/* Telemart row */}
            {startTelemart && <div className="flex items-center px-4 py-3 justify-between border-b border-white/[0.06] hover:bg-white/[0.02] transition-colors">
              <div className="flex items-center gap-3">
                <div className="w-8 h-8 rounded-[8px] bg-gradient-to-b from-[#5E5CE6] to-[#4B49B8] flex items-center justify-center shadow-sm border border-white/20">
                  <Monitor size={16} strokeWidth={2.5} />
                </div>
                <div className="flex flex-col">
                  <span className="font-medium text-[14px] text-white leading-tight">Telemart App</span>
                  <span className="text-[12px] mt-0.5 transition-colors" style={{ color: STATE_COLOR[telemart.state] }}>
                    {telemart.text || t('status_waiting')}
                  </span>
                </div>
              </div>
              {telemart.state === 'working' ? (
                <button
                  onClick={() => api().telemart_cancel()}
                  className="text-[12px] font-medium px-3 py-1 rounded-[6px] border transition-colors bg-[#FF453A]/15 hover:bg-[#FF453A]/25 text-[#FF453A] border-[#FF453A]/30"
                >
                  {t('cancel')}
                </button>
              ) : (
                <button
                  onClick={() => api().telemart_start()}
                  disabled={isBusy || monitor.state !== 'success'}
                  title={monitor.state !== 'success' ? t('monitor_wait') : undefined}
                  className="text-[12px] font-medium px-3 py-1 rounded-[6px] border transition-colors bg-[#0A84FF] hover:bg-[#007AFF] disabled:opacity-50 disabled:cursor-not-allowed text-white border-[#0A84FF]"
                >
                  {t('launch')}
                </button>
              )}
            </div>}

            {/* Monitor row */}
            <div className="flex items-center px-4 py-3 justify-between hover:bg-white/[0.02] transition-colors">
              <div className="flex items-center gap-3">
                <div className="w-8 h-8 rounded-[8px] bg-gradient-to-b from-[#8E8E93] to-[#636366] flex items-center justify-center shadow-sm border border-white/20">
                  <Activity size={16} strokeWidth={2.5} />
                </div>
                <div className="flex flex-col">
                  <span className="font-medium text-[14px] text-white leading-tight">{t('system_monitor')}</span>
                  <span className="text-[12px] mt-0.5 transition-colors" style={{ color: STATE_COLOR[monitor.state] }}>
                    {monitor.text || t('status_waiting')}
                  </span>
                </div>
              </div>
              <div
                className={`w-2 h-2 rounded-full ${
                  monitor.state === 'success'
                    ? 'bg-[#34C759] shadow-[0_0_8px_rgba(52,199,89,0.8)] animate-pulse'
                    : monitor.state === 'working'
                    ? 'bg-[#FF9F0A] animate-pulse'
                    : 'bg-white/20'
                }`}
              />
            </div>

            {/* Profile statuses */}
            <AnimatePresence>
              {Object.keys(profileStatuses).length > 0 && (
                <motion.div
                  key="profile-statuses"
                  initial={{ opacity: 0, height: 0 }}
                  animate={{ opacity: 1, height: 'auto' }}
                  exit={{ opacity: 0, height: 0 }}
                  transition={{ duration: 0.25, ease: 'easeInOut' }}
                  className="overflow-hidden"
                >
                  <div className="flex flex-wrap gap-x-3 gap-y-1.5 px-4 py-2.5 border-t border-white/[0.06] bg-black/10">
                    {Object.entries(profileStatuses).map(([name, status]) => {
                      const color =
                        status === 'active' ? '#34C759' :
                        status === 'connecting' || status === 'authenticating' ? '#FF9F0A' :
                        status === 'error' ? '#FF453A' : '#ffffff33';
                      return (
                        <span key={name} className="flex items-center gap-1.5 text-[11px] text-white/60">
                          <span style={{ width: 6, height: 6, borderRadius: '50%', background: color, display: 'inline-block', flexShrink: 0, boxShadow: status === 'active' ? `0 0 4px ${color}` : 'none' }} />
                          {name}
                        </span>
                      );
                    })}
                  </div>
                </motion.div>
              )}
            </AnimatePresence>
          </div>

          {/* Activity log */}
          <div className="flex-1 flex flex-col min-h-[160px]">
            <div className="flex items-center gap-1.5 mb-2 px-1">
              <Terminal size={12} className="text-white/50" />
              <span className="text-[11px] font-semibold text-white/50 uppercase tracking-wider">{t('activity_log')}</span>
            </div>
            <div
              ref={logRef}
              className="flex-1 bg-black/40 rounded-[10px] border border-white/[0.05] p-3 font-mono text-[11px] overflow-y-auto shadow-[inset_0_2px_10px_rgba(0,0,0,0.2)]"
            >
              <div className="flex flex-col gap-1 leading-relaxed">
                {logs.length === 0 ? (
                  <span className="text-white/30">{t('system_ready')}</span>
                ) : (
                  logs.map((line, i) => (
                    <span key={i} className="text-white/65">{line}</span>
                  ))
                )}
                <span className="text-white/40 animate-pulse">_</span>
              </div>
            </div>
          </div>
        </main>

        {/* Footer */}
        <footer className="h-[40px] bg-white/[0.02] border-t border-white/[0.08] flex items-center justify-between px-4 shrink-0">
          <div className="flex items-center gap-1.5">
            <Wifi size={12} className={net.connected ? 'text-[#34C759]' : 'text-white/40'} />
            <span className="text-[11px] text-white/60 font-medium">
              {net.connected ? 'Інтернет підключено' : 'Немає з\'єднання'}
            </span>
          </div>
          <div className="flex items-center gap-1.5">
            <Activity size={12} className="text-white/40" />
            <span className="text-[11px] text-white/60 font-medium">
              Ping: <span className="text-white">{net.ping !== null ? `${net.ping}ms` : '--'}</span>
            </span>
          </div>
        </footer>

        {/* Settings overlay */}
        {showSettings && (
          <SettingsModal
            onClose={() => setShowSettings(false)}
            hasPin={hasPin}
            userPin={userPin}
            onSaved={(st, lng) => { onStartTelematChange?.(st); onLangChange?.(lng); }}
            onPinChanged={onPinChanged}
          />
        )}
      </div>
    </div>
  );
}

// ── Root App ───────────────────────────────────────────────────────────────
export default function App() {
  const [view, setView] = useState<View>('loading');
  const [pritunl, setPritunl] = useState<Panel>({ state: 'off', text: '' });
  const [telemart, setTelemart] = useState<Panel>({ state: 'off', text: '' });
  const [monitor, setMonitor] = useState<Panel>({ state: 'off', text: '' });
  const [net, setNet] = useState({ connected: false, ping: null as number | null });
  const [vpnConnected, setVpnConnected] = useState(false);
  const [isBusy, setIsBusy] = useState(false);
  const [updateTag, setUpdateTag] = useState<string | null>(null);
  const [logs, setLogs] = useState<string[]>([]);
  const [userPin, setUserPin] = useState('');
  const [version, setVersion] = useState('v?');
  const [startTelemart, setStartTelemart] = useState(true);
  const [profileStatuses, setProfileStatuses] = useState<Record<string, string>>({});
  const [lang, setLang] = useState<Lang>('ua');
  const logRef = useRef<HTMLDivElement>(null);

  const addLog = useCallback((msg: string) => {
    setLogs(prev => [...prev.slice(-300), `${ts()} ${msg}`]);
  }, []);

  // Auto-scroll log
  useEffect(() => {
    if (logRef.current) {
      logRef.current.scrollTop = logRef.current.scrollHeight;
    }
  }, [logs]);

  // Register __update handler (Python → JS)
  useEffect(() => {
    window.__update = (data: any) => {
      switch (data.type) {
        case 'init':
          setView(data.view as View);
          if (data.version) setVersion(data.version);
          if (data.start_telemart !== undefined) setStartTelemart(data.start_telemart);
          if (data.language) setLang(data.language as Lang);
          break;
        case 'status': {
          const panel: Panel = { state: data.state as PanelState, text: data.text };
          if (data.target === 'pritunl') setPritunl(panel);
          else if (data.target === 'telemart') setTelemart(panel);
          else if (data.target === 'monitor') setMonitor(panel);
          addLog(data.text);
          break;
        }
        case 'buttons':
          setIsBusy(data.is_busy);
          setVpnConnected(data.vpn_connected);
          break;
        case 'net_status':
          setNet({ connected: data.connected, ping: data.ping });
          break;
        case 'profile_status':
          setProfileStatuses(data.profiles ?? {});
          break;
        case 'update_found':
          setUpdateTag(data.tag);
          addLog(`Доступне оновлення ${data.tag}`);
          break;
        case 'log':
          addLog(data.message);
          break;
        case 'update_done':
          addLog('Оновлення застосовано. Перезапуск...');
          break;
        case 'update_failed':
          addLog('Помилка оновлення.');
          break;
        case 'shutdown':
          setView('shutdown');
          break;
      }
    };
  }, [addLog]);

  // Init: wait for pywebview, then get initial state
  useEffect(() => {
    const init = async () => {
      const state = await api().get_initial_state();
      setView(state.view);
      if (state.language) setLang(state.language as Lang);
      if (state.start_telemart !== undefined) setStartTelemart(state.start_telemart);
      if (state.version) setVersion(state.version);
    };
    if (window.pywebview) {
      init();
    } else {
      window.addEventListener('pywebviewready', init, { once: true });
    }
  }, []);

  // DEV: view switcher (no pywebview = preview mode)
  const isPreview = !window.pywebview;
  const DevBar = () => (
    <div className="fixed bottom-3 left-1/2 -translate-x-1/2 z-[9999] flex gap-1 bg-black/70 backdrop-blur border border-white/10 rounded-full px-3 py-1.5">
      {(['main','pin','config','shutdown'] as View[]).map(v => (
        <button key={v} onClick={() => setView(v)}
          className={`text-[11px] px-2.5 py-0.5 rounded-full transition-colors ${view === v ? 'bg-white/20 text-white' : 'text-white/40 hover:text-white/70'}`}
        >{v}</button>
      ))}
    </div>
  );

  return (
    <LangContext.Provider value={lang}>
      {isPreview && <DevBar />}
      <AnimatePresence mode="wait">
        {view === 'loading' && (
          <motion.div key="loading" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }} transition={{ duration: 0.2 }} style={{ position: 'fixed', inset: 0 }} className="flex items-center justify-center">
            <span className="text-white/30 text-sm font-mono animate-pulse">Loading...</span>
          </motion.div>
        )}
        {view === 'config' && (
          <motion.div key="config" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }} transition={{ duration: 0.2 }} style={{ position: 'fixed', inset: 0 }}>
            <ConfigView onDone={nextView => { setView(nextView); addLog('Налаштування збережені.'); }} />
          </motion.div>
        )}
        {view === 'pin' && (
          <motion.div key="pin" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }} transition={{ duration: 0.2 }} style={{ position: 'fixed', inset: 0 }}>
            <PinView onDone={(pin, st, lng) => { setUserPin(pin); setStartTelemart(st); if (lng) setLang(lng as Lang); setView('main'); }} />
          </motion.div>
        )}
        {view === 'shutdown' && (
          <motion.div key="shutdown" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }} transition={{ duration: 0.2 }} style={{ position: 'fixed', inset: 0 }}>
            <ShutdownView />
          </motion.div>
        )}
        {view === 'main' && (
          <motion.div key="main" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }} transition={{ duration: 0.2 }} style={{ position: 'fixed', inset: 0 }}>
            <MainView pritunl={pritunl} telemart={telemart} monitor={monitor} net={net} vpnConnected={vpnConnected} isBusy={isBusy} updateTag={updateTag} logs={logs} logRef={logRef} userPin={userPin} version={version} startTelemart={startTelemart} profileStatuses={profileStatuses} onOpenConfig={() => setView('config')} onStartTelematChange={setStartTelemart} onLangChange={v => setLang(v as Lang)} onPinChanged={setUserPin} />
          </motion.div>
        )}
      </AnimatePresence>
    </LangContext.Provider>
  );
}
