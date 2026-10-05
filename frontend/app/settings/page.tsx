"use client";

import { useState, useEffect, useRef } from "react";
import { AppShell } from "@/src/components/layout/app-shell";
import { User, Bell, Shield, Key, Building, Loader2 } from "lucide-react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { usersApi } from "@/src/lib/api/users";
import { toast } from "react-hot-toast";

export default function Settings() {
  const queryClient = useQueryClient();
  const [activeTab, setActiveTab] = useState("profile");
  
  const { data: user, isLoading } = useQuery({
    queryKey: ['user_me'],
    queryFn: usersApi.getMe,
  });

  const [firstName, setFirstName] = useState("");
  const [lastName, setLastName] = useState("");
  const [email, setEmail] = useState("");
  const fileInputRef = useRef<HTMLInputElement>(null);

  // React-endorsed "adjust state when props/data change" pattern (render-phase
  // update) instead of a setState-in-effect call.
  const [syncedUser, setSyncedUser] = useState<typeof user>(undefined);
  if (user && user !== syncedUser) {
    setSyncedUser(user);
    const parts = user.full_name.split(" ");
    setFirstName(parts[0] || "");
    setLastName(parts.slice(1).join(" ") || "");
    setEmail(user.email || "");
  }

  const updateProfileMutation = useMutation({
    mutationFn: usersApi.updateMe,
    onSuccess: (data) => {
      queryClient.setQueryData(['user_me'], data);
      toast.success("Profile updated successfully");
    },
    onError: () => toast.error("Failed to update profile"),
  });

  const updateAvatarMutation = useMutation({
    mutationFn: usersApi.updateAvatar,
    onSuccess: (data) => {
      queryClient.setQueryData(['user_me'], data);
      toast.success("Avatar updated successfully");
    },
    onError: () => toast.error("Failed to upload avatar"),
  });

  const handleSaveProfile = () => {
    updateProfileMutation.mutate({ first_name: firstName, last_name: lastName, email });
  };

  const handleAvatarChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files.length > 0) {
      updateAvatarMutation.mutate(e.target.files[0]);
    }
  };

  const navItems = [
    { id: "profile", label: "Profile", icon: <User className="h-4 w-4" /> },
    { id: "organization", label: "Organization", icon: <Building className="h-4 w-4" /> },
    { id: "security", label: "Security", icon: <Shield className="h-4 w-4" /> },
    { id: "notifications", label: "Notifications", icon: <Bell className="h-4 w-4" /> },
    { id: "api-keys", label: "API Keys", icon: <Key className="h-4 w-4" /> }
  ];

  return (
    <AppShell>
      <div className="mb-6">
        <h1 className="text-2xl sm:text-3xl font-bold text-slate-900 tracking-tight">Settings</h1>
        <p className="text-slate-700/60 mt-1 font-medium">Manage your account, organization, and preferences.</p>
      </div>

      <div className="flex flex-col md:flex-row gap-8">
        <div className="w-full md:w-64 shrink-0">
          <nav className="space-y-1">
            {navItems.map(item => (
              <button
                key={item.id}
                onClick={() => setActiveTab(item.id)}
                className={`flex items-center gap-3 px-3 py-2.5 w-full text-left rounded-lg font-semibold text-sm transition-colors border ${
                  activeTab === item.id
                    ? "bg-white text-blue-600 shadow-sm border-slate-200"
                    : "text-slate-700/80 border-transparent hover:bg-slate-200/50 hover:text-slate-900"
                }`}
              >
                {item.icon} {item.label}
              </button>
            ))}
          </nav>
        </div>

        <div className="flex-1 space-y-6">
          {activeTab === "profile" && (
            <>
              <div className="bg-white rounded-xl border border-slate-200 shadow-sm overflow-hidden">
                <div className="p-5 border-b border-slate-200 bg-slate-50">
                  <h3 className="font-bold text-slate-900">Profile Information</h3>
                  <p className="text-sm text-slate-700/60 mt-1 font-medium">Update your account details and email address.</p>
                </div>
                <div className="p-5 sm:p-6 space-y-6">
                  {isLoading ? (
                    <div className="flex justify-center p-4"><Loader2 className="h-6 w-6 animate-spin text-blue-600" /></div>
                  ) : (
                    <>
                      <div className="flex items-center gap-5">
                        <div className="h-16 w-16 rounded-full bg-gradient-to-br from-blue-600 to-indigo-600 flex items-center justify-center text-white text-xl font-bold shadow-sm border-2 border-white ring-2 ring-slate-100 overflow-hidden relative group">
                          {user?.avatar_url ? (
                             <img src={`${process.env.NEXT_PUBLIC_API_URL || (process.env.NODE_ENV === "production" ? "https://legalgpt-backend.fastapicloud.dev" : "http://localhost:8000")}${user.avatar_url}`} alt="Avatar" className="w-full h-full object-cover" />
                          ) : (
                             <span>{firstName?.[0] || 'U'}</span>
                          )}
                          <div className="absolute inset-0 bg-black/40 hidden group-hover:flex items-center justify-center cursor-pointer transition-all" onClick={() => fileInputRef.current?.click()}>
                            <span className="text-[10px]">Edit</span>
                          </div>
                        </div>
                        <div>
                          <input type="file" ref={fileInputRef} className="hidden" accept="image/*" onChange={handleAvatarChange} />
                          <button 
                            onClick={() => fileInputRef.current?.click()}
                            disabled={updateAvatarMutation.isPending}
                            className="px-3 py-1.5 bg-white border border-slate-200/80 text-slate-700 rounded-md hover:bg-slate-50 font-medium text-sm transition-colors shadow-sm outline-none focus:ring-2 focus:ring-blue-500 disabled:opacity-50">
                            {updateAvatarMutation.isPending ? 'Uploading...' : 'Change Avatar'}
                          </button>
                        </div>
                      </div>

                      <div className="grid grid-cols-1 sm:grid-cols-2 gap-6">
                        <div>
                          <label className="block text-sm font-bold text-slate-700 mb-2">First Name</label>
                          <input type="text" value={firstName} onChange={e => setFirstName(e.target.value)} className="w-full px-3 py-2 border border-slate-200/80 rounded-md text-sm outline-none focus:border-blue-500 focus:ring-1 focus:ring-blue-500 transition-all bg-white" />
                        </div>
                        <div>
                          <label className="block text-sm font-bold text-slate-700 mb-2">Last Name</label>
                          <input type="text" value={lastName} onChange={e => setLastName(e.target.value)} className="w-full px-3 py-2 border border-slate-200/80 rounded-md text-sm outline-none focus:border-blue-500 focus:ring-1 focus:ring-blue-500 transition-all bg-white" />
                        </div>
                        <div className="sm:col-span-2">
                          <label className="block text-sm font-bold text-slate-700 mb-2">Email Address</label>
                          <input type="email" value={email} onChange={e => setEmail(e.target.value)} className="w-full px-3 py-2 border border-slate-200/80 rounded-md text-sm outline-none focus:border-blue-500 focus:ring-1 focus:ring-blue-500 transition-all bg-white" />
                        </div>
                      </div>
                    </>
                  )}
                </div>
                <div className="p-4 sm:p-5 border-t border-slate-200 bg-slate-50 flex justify-end">
                  <button 
                    onClick={handleSaveProfile}
                    disabled={updateProfileMutation.isPending}
                    className="px-5 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-600/90 font-medium text-sm transition-colors shadow-sm outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-1 disabled:opacity-50">
                    {updateProfileMutation.isPending ? 'Saving...' : 'Save Changes'}
                  </button>
                </div>
              </div>

              <div className="bg-white rounded-xl border border-slate-200 shadow-sm overflow-hidden">
                <div className="p-5 border-b border-slate-200 bg-slate-50">
                  <h3 className="font-bold text-slate-900">Preferences</h3>
                  <p className="text-sm text-slate-700/60 mt-1 font-medium">Manage your application experience.</p>
                </div>
                <div className="p-5 sm:p-6 space-y-5">
                  <div className="flex items-center justify-between">
                    <div>
                      <h4 className="text-sm font-bold text-slate-900">Email Notifications</h4>
                      <p className="text-sm text-slate-700/60 mt-0.5 font-medium">Receive email alerts when a contract analysis is complete.</p>
                    </div>
                    <div className="relative inline-block w-10 mr-2 align-middle select-none transition duration-200 ease-in">
                      <input type="checkbox" name="toggle" id="toggle1" defaultChecked className="toggle-checkbox absolute block w-5 h-5 rounded-full bg-white border-4 border-blue-600 appearance-none cursor-pointer translate-x-5 transition-transform" />
                      <label htmlFor="toggle1" className="toggle-label block overflow-hidden h-5 rounded-full bg-blue-600 cursor-pointer"></label>
                    </div>
                  </div>
                  <div className="pt-4 border-t border-slate-100 flex items-center justify-between">
                    <div>
                      <h4 className="text-sm font-bold text-slate-900">Compact View</h4>
                      <p className="text-sm text-slate-700/60 mt-0.5 font-medium">Use less whitespace in tables and lists.</p>
                    </div>
                    <div className="relative inline-block w-10 mr-2 align-middle select-none transition duration-200 ease-in">
                      <input type="checkbox" name="toggle2" id="toggle2" className="toggle-checkbox absolute block w-5 h-5 rounded-full bg-white border-4 border-slate-200/80 appearance-none cursor-pointer transition-transform" />
                      <label htmlFor="toggle2" className="toggle-label block overflow-hidden h-5 rounded-full bg-slate-300 cursor-pointer"></label>
                    </div>
                  </div>
                </div>
              </div>
            </>
          )}

          {activeTab !== "profile" && (
            <div className="bg-white rounded-xl border border-slate-200 shadow-sm overflow-hidden p-10 flex flex-col items-center justify-center text-slate-700/60">
              <div className="h-12 w-12 bg-slate-50 rounded-full flex items-center justify-center mb-3">
                {navItems.find(i => i.id === activeTab)?.icon}
              </div>
              <h3 className="font-bold text-slate-900">Coming Soon</h3>
              <p className="text-sm mt-1">This section is currently under development.</p>
            </div>
          )}
        </div>
      </div>
    </AppShell>
  );
}
