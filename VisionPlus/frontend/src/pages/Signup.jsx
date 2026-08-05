import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { MdVisibility, MdVisibilityOff, MdShield } from "react-icons/md";
import toast from "react-hot-toast";
import { register } from "../services/api";

export default function Signup() {

    const navigate = useNavigate();

    const [showPassword, setShowPassword] = useState(false);

    const [form, setForm] = useState({
        full_name: "",
        email: "",
        password: "",
        confirmPassword: "",
    });

    const handleChange = (e) => {
        setForm({
            ...form,
            [e.target.name]: e.target.value,
        });
    };

    const handleSubmit = async (e) => {
        e.preventDefault();

        if (form.password !== form.confirmPassword) {
            toast.error("Passwords do not match");
            return;
        }

        if (form.password.length < 8) {
            toast.error("Password must be at least 8 characters");
            return;
        }

        try {

            await register(
                form.full_name,
                form.email,
                form.password
            );

            toast.success("Registration Successful!");

            navigate("/login");

        } catch (err) {

            toast.error(
                err.response?.data?.detail ||
                "Registration Failed"
            );

        }
    };

    return (

        <div className="flex min-h-screen items-center justify-center bg-surface p-6">

            <div className="w-full max-w-md rounded-xl bg-surface-card p-8 shadow-2xl">

                <div className="mb-6 flex items-center gap-3">

                    <div className="rounded-lg bg-primary p-2">
                        <MdShield className="text-white text-xl"/>
                    </div>

                    <h1 className="text-2xl font-bold text-white">
                        Create Account
                    </h1>

                </div>

                <form
                    onSubmit={handleSubmit}
                    className="space-y-4"
                >

                    <input
                        name="full_name"
                        placeholder="Full Name"
                        onChange={handleChange}
                        className="w-full rounded-lg border bg-surface px-4 py-3 text-white"
                        required
                    />

                    <input
                        type="email"
                        name="email"
                        placeholder="Email"
                        onChange={handleChange}
                        className="w-full rounded-lg border bg-surface px-4 py-3 text-white"
                        required
                    />

                    <div className="relative">

                        <input
                            type={showPassword ? "text" : "password"}
                            name="password"
                            placeholder="Password"
                            onChange={handleChange}
                            className="w-full rounded-lg border bg-surface px-4 py-3 text-white"
                            required
                        />

                        <button
                            type="button"
                            onClick={() =>
                                setShowPassword(!showPassword)
                            }
                            className="absolute right-4 top-4 text-slate-400"
                        >
                            {showPassword
                                ? <MdVisibilityOff/>
                                : <MdVisibility/>}
                        </button>

                    </div>

                    <input
                        type="password"
                        name="confirmPassword"
                        placeholder="Confirm Password"
                        onChange={handleChange}
                        className="w-full rounded-lg border bg-surface px-4 py-3 text-white"
                        required
                    />

                    <button
                        className="w-full rounded-lg bg-primary py-3 font-semibold text-white"
                    >
                        Create Account
                    </button>

                </form>

                <p className="mt-6 text-center text-slate-400">

                    Already have an account?

                    <Link
                        to="/login"
                        className="ml-2 text-primary font-semibold"
                    >
                        Login
                    </Link>

                </p>

            </div>

        </div>

    );

}