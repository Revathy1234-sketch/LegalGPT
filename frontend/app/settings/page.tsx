import { AppShell } from "@/src/components/layout/app-shell";
import { User, Bell, Shield, Key, Building } from "lucide-react";

export default function Settings() {
  return (
    <AppShell>
      <div className="mb-6">
        <h1 className="text-2xl sm:text-3xl font-bold text-slate-900 tracking-tight">Settings</h1>
        <p className="text-slate-500 mt-1 font-medium">Manage your account, organization, and preferences.</p>
      </div>

      <div className="flex flex-col md:flex-row gap-8">
        <div className="w-full md:w-64 shrink-0">
          <nav className="space-y-1">
            <a href="#" className="flex items-center gap-3 px-3 py-2.5 bg-white text-blue-600 rounded-lg font-bold text-sm shadow-sm border border-slate-200">
              <User className="h-4 w-4" /> Profile
            </a>
            <a href="#" className="flex items-center gap-3 px-3 py-2.5 text-slate-600 hover:bg-slate-200/50 hover:text-slate-900 rounded-lg font-semibold text-sm transition-colors border border-transparent">
              <Building className="h-4 w-4" /> Organization
            </a>
            <a href="#" className="flex items-center gap-3 px-3 py-2.5 text-slate-600 hover:bg-slate-200/50 hover:text-slate-900 rounded-lg font-semibold text-sm transition-colors border border-transparent">
              <Shield className="h-4 w-4" /> Security
            </a>
            <a href="#" className="flex items-center gap-3 px-3 py-2.5 text-slate-600 hover:bg-slate-200/50 hover:text-slate-900 rounded-lg font-semibold text-sm transition-colors border border-transparent">
              <Bell className="h-4 w-4" /> Notifications
            </a>
            <a href="#" className="flex items-center gap-3 px-3 py-2.5 text-slate-600 hover:bg-slate-200/50 hover:text-slate-900 rounded-lg font-semibold text-sm transition-colors border border-transparent">
              <Key className="h-4 w-4" /> API Keys
            </a>
          </nav>
        </div>

        <div className="flex-1 space-y-6">
          <div className="bg-white rounded-xl border border-slate-200 shadow-sm overflow-hidden">
            <div className="p-5 border-b border-slate-200 bg-slate-50">
              <h3 className="font-bold text-slate-900">Profile Information</h3>
              <p className="text-sm text-slate-500 mt-1 font-medium">Update your account details and email address.</p>
            </div>
            <div className="p-5 sm:p-6 space-y-6">
              <div className="flex items-center gap-5">
                <div className="h-16 w-16 rounded-full bg-gradient-to-br from-blue-600 to-indigo-600 flex items-center justify-center text-white text-xl font-bold shadow-sm border-2 border-white ring-2 ring-slate-100">
                  JD
                </div>
                <div>
                  <button className="px-3 py-1.5 bg-white border border-slate-300 text-slate-700 rounded-md hover:bg-slate-50 font-medium text-sm transition-colors shadow-sm outline-none focus:ring-2 focus:ring-blue-500">
                    Change Avatar
                  </button>
                </div>
              </div>

              <div className="grid grid-cols-1 sm:grid-cols-2 gap-6">
                <div>
                  <label className="block text-sm font-bold text-slate-700 mb-2">First Name</label>
                  <input type="text" defaultValue="John" className="w-full px-3 py-2 border border-slate-300 rounded-md text-sm outline-none focus:border-blue-500 focus:ring-1 focus:ring-blue-500 transition-all bg-white" />
                </div>
                <div>
                  <label className="block text-sm font-bold text-slate-700 mb-2">Last Name</label>
                  <input type="text" defaultValue="Doe" className="w-full px-3 py-2 border border-slate-300 rounded-md text-sm outline-none focus:border-blue-500 focus:ring-1 focus:ring-blue-500 transition-all bg-white" />
                </div>
                <div className="sm:col-span-2">
                  <label className="block text-sm font-bold text-slate-700 mb-2">Email Address</label>
                  <input type="email" defaultValue="john.doe@example.com" className="w-full px-3 py-2 border border-slate-300 rounded-md text-sm outline-none focus:border-blue-500 focus:ring-1 focus:ring-blue-500 transition-all bg-white" />
                </div>
              </div>
            </div>
            <div className="p-4 sm:p-5 border-t border-slate-200 bg-slate-50 flex justify-end">
              <button className="px-5 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 font-medium text-sm transition-colors shadow-sm outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-1">
                Save Changes
              </button>
            </div>
          </div>

          <div className="bg-white rounded-xl border border-slate-200 shadow-sm overflow-hidden">
            <div className="p-5 border-b border-slate-200 bg-slate-50">
              <h3 className="font-bold text-slate-900">Preferences</h3>
              <p className="text-sm text-slate-500 mt-1 font-medium">Manage your application experience.</p>
            </div>
            <div className="p-5 sm:p-6 space-y-5">
              <div className="flex items-center justify-between">
                <div>
                  <h4 className="text-sm font-bold text-slate-900">Email Notifications</h4>
                  <p className="text-sm text-slate-500 mt-0.5 font-medium">Receive email alerts when a contract analysis is complete.</p>
                </div>
                <div className="relative inline-block w-10 mr-2 align-middle select-none transition duration-200 ease-in">
                  <input type="checkbox" name="toggle" id="toggle1" defaultChecked className="toggle-checkbox absolute block w-5 h-5 rounded-full bg-white border-4 border-blue-600 appearance-none cursor-pointer translate-x-5 transition-transform" />
                  <label htmlFor="toggle1" className="toggle-label block overflow-hidden h-5 rounded-full bg-blue-600 cursor-pointer"></label>
                </div>
              </div>
              <div className="pt-4 border-t border-slate-100 flex items-center justify-between">
                <div>
                  <h4 className="text-sm font-bold text-slate-900">Compact View</h4>
                  <p className="text-sm text-slate-500 mt-0.5 font-medium">Use less whitespace in tables and lists.</p>
                </div>
                <div className="relative inline-block w-10 mr-2 align-middle select-none transition duration-200 ease-in">
                  <input type="checkbox" name="toggle2" id="toggle2" className="toggle-checkbox absolute block w-5 h-5 rounded-full bg-white border-4 border-slate-300 appearance-none cursor-pointer transition-transform" />
                  <label htmlFor="toggle2" className="toggle-label block overflow-hidden h-5 rounded-full bg-slate-300 cursor-pointer"></label>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </AppShell>
  );
}
