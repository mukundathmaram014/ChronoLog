import { Navbar } from "./Components/Navbar"
import { InstallPrompt } from "./Components/InstallPrompt"
import { Outlet } from "react-router-dom"

export function Layout() {
    return (
        <>
            <Navbar/>
            <main>
                <Outlet/>
            </main>
            <InstallPrompt/>
        </>
    )
}