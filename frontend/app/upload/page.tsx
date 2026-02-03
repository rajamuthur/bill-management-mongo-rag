"use client";
import { useState, useEffect } from "react";

type Item = {
  description: string;
  quantity: string | number;
  amount: string | number;
};

export default function UploadPage() {
  const [mode, setMode] = useState<"file" | "manual">("file");
  const [items, setItems] = useState<Item[]>([]);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [fileName, setFileName] = useState<string | null>(null);

  function addItem() {
    setItems([...items, { description: "", quantity: "", amount: "" }]);
  }

  function updateItem(index: number, field: keyof Item, value: any) {
    const updated = [...items];
    updated[index] = { ...updated[index], [field]: value };
    setItems(updated);
  }

  function removeItem(index: number) {
    setItems(items.filter((_, i) => i !== index));
  }

  /* Camera Logic */
  const [showCamera, setShowCamera] = useState(false);
  const [cameraStream, setCameraStream] = useState<MediaStream | null>(null);

  const startCamera = async () => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ video: true });
      setCameraStream(stream);
      setShowCamera(true);
    } catch (err) {
      console.error("Error accessing camera:", err);
      alert("Could not access camera. Please allow camera permissions.");
    }
  };

  const stopCamera = () => {
    if (cameraStream) {
      cameraStream.getTracks().forEach(track => track.stop());
      setCameraStream(null);
    }
    setShowCamera(false);
  };

  const capturePhoto = () => {
    const video = document.querySelector("video");
    if (video) {
      const canvas = document.createElement("canvas");
      canvas.width = video.videoWidth;
      canvas.height = video.videoHeight;
      const ctx = canvas.getContext("2d");
      if (ctx) {
        ctx.drawImage(video, 0, 0, canvas.width, canvas.height);
        canvas.toBlob((blob) => {
          if (blob) {
            const file = new File([blob], `capture-${Date.now()}.jpg`, { type: "image/jpeg" });

            // Manually trigger the file input change simulation or just set the fileName state
            // Since we can't easily programmatically set file input value, we'll need to append this file 
            // to the formData manually in uploadBill or store it in a state.
            // Let's store it in a state 'capturedFile' and prefer it over the input file.
            setCapturedFile(file);
            setFileName(file.name);
            stopCamera();
          }
        }, "image/jpeg");
      }
    }
  };

  const [capturedFile, setCapturedFile] = useState<File | null>(null);
  const [confirmationData, setConfirmationData] = useState<any>(null);
  const [extractionError, setExtractionError] = useState<string | null>(null);
  const [showSuccess, setShowSuccess] = useState(false);
  const [editedFields, setEditedFields] = useState<any>({});
  const [errors, setErrors] = useState<any>({});
  const [showPreview, setShowPreview] = useState(false);

  // Initialize edited fields when confirmation data arrives
  useEffect(() => {
    if (confirmationData?.extracted) {
      setEditedFields(confirmationData.extracted);
      setErrors({});
    }
  }, [confirmationData]);

  const handleFieldChange = (key: string, value: any) => {
    setEditedFields((prev: any) => ({
      ...prev,
      [key]: value
    }));
    // Clear error for this field
    if (errors[key]) {
      setErrors((prev: any) => ({ ...prev, [key]: null }));
    }
  };

  async function uploadBill(e: any) {
    e.preventDefault();

    // 🔴 VALIDATION: Check if manual mode requires at least one item
    if (mode === 'manual' && items.length === 0) {
      alert("Please add at least one bill detail item before submitting.");
      return;
    }

    setIsSubmitting(true);
    const formData = new FormData(e.target);

    // If we have a captured file via camera, append it
    if (capturedFile && mode === 'file') {
      formData.set("file", capturedFile);
    }

    // attach items only if present
    if (items.length > 0) {
      formData.append("items", JSON.stringify(items));
    }

    // 🔴 DATE FIX (MANUAL): Ensure ISO format
    if (mode === 'manual') {
      const dateVal = formData.get("bill_date") as string;
      if (dateVal) {
        formData.set("bill_date", new Date(dateVal).toISOString().replace('Z', '+00:00'));
      }
    }

    try {
      const res = await fetch("/api/upload", {
        method: "POST",
        body: formData
      });
      const data = await res.json();

      if (data.status === "requires_confirmation") {
        setConfirmationData(data);
        setShowPreview(true); // Default to showing preview
        setEditedFields({
          ...data.extracted,
          items: data.extracted.items || []
        });
      } else if (data.status === "extraction_failed") {
        setExtractionError(data.message || "Could not extract any text. Please try again or use Manual Entry.");
        // Clear uploaded file on failure
        setCapturedFile(null);
        setFileName(null);
        e.target.reset();
      } else {
        // Success for Manual or Direct Upload
        setShowSuccess(true);
        setCapturedFile(null);
        setFileName(null);
        setItems([]); // Clear items
        e.target.reset(); // Reset form
      }
    } catch (err) {
      console.error(err);
      alert("Failed to upload");
      // Clear uploaded file on error
      setCapturedFile(null);
      setFileName(null);
      e.target.reset();
    } finally {
      setIsSubmitting(false);
    }
  }

  // --- Item Helpers for Modal ---
  const addModalItem = () => {
    const currentItems = editedFields.items || [];
    const newItems = [...currentItems, { description: "", quantity: 1, amount: 0 }];
    handleFieldChange("items", newItems);
  };

  const removeModalItem = (index: number) => {
    if (!editedFields.items) return;
    const newItems = editedFields.items.filter((_: any, i: number) => i !== index);
    handleFieldChange("items", newItems);
  };

  const updateModalItem = (index: number, field: string, value: any) => {
    if (!editedFields.items) return;
    const newItems = [...editedFields.items];
    newItems[index] = { ...newItems[index], [field]: value };
    handleFieldChange("items", newItems);
  };

  async function handleConfirmSave() {
    if (!confirmationData) return;

    // VALIDATION
    const required = ["vendor", "bill_date", "total_amount", "payment_method"];
    const newErrors: any = {};
    let hasError = false;

    required.forEach(field => {
      if (!editedFields[field]) {
        newErrors[field] = "Required";
        hasError = true;
      }
    });

    if (!editedFields.items || editedFields.items.length === 0) {
      newErrors["items"] = "Add at least one item";
      hasError = true;
    } else {
      // Check if item has quantity/amount
      const validItems = editedFields.items.some((i: any) => i.quantity > 0 || i.amount > 0);
      if (!validItems) {
        newErrors["items"] = "At least one item needs valid Qty/Amt";
        hasError = true;
      }
    }

    if (hasError) {
      setErrors(newErrors);
      return;
    }

    setIsSubmitting(true);
    try {
      // 🔴 DATE FIX: Ensure ISO format for backend consistency
      const finalExtracted = { ...editedFields };
      if (finalExtracted.bill_date) {
        // Input is YYYY-MM-DD, manually ensure ISO with +00:00 as requested
        finalExtracted.bill_date = new Date(finalExtracted.bill_date).toISOString().replace('Z', '+00:00');
      }

      const res = await fetch("/api/ingest/confirm", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          user_id: "u1", // Todo: dynamic
          extracted: finalExtracted,
          raw_text: confirmationData.raw_text,
          file_path: confirmationData.file_path,
          // Generate a new ID if backend didn't provide one (ingest_service case)
          bill_id: confirmationData.bill_id || `bill_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`
        })
      });
      const result = await res.json();
      if (result.status === "ok") {
        setShowSuccess(true); // Show success modal instead of alert
        setConfirmationData(null);
        setCapturedFile(null);
        setFileName(null);
        setEditedFields({});
        setErrors({});
      } else {
        alert("Failed to save.");
      }
    } catch (err) {
      console.error(err);
      alert("Error confirming save");
    } finally {
      setIsSubmitting(false);
    }
  }

  return (
    <div className="max-w-3xl mx-auto">
      <div className="mb-8 text-center">
        <h1 className="text-3xl font-extrabold text-slate-900">Add New Bill</h1>
        <p className="text-slate-500 mt-2">Upload a receipt, take a photo, or manually enter expense details.</p>
      </div>

      <div className="bg-white rounded-2xl shadow-xl shadow-indigo-100/50 border border-slate-100 overflow-hidden">
        {/* Tabs */}
        <div className="flex border-b border-slate-100">
          <button
            type="button"
            onClick={() => { setMode("file"); stopCamera(); }}
            className={`flex-1 py-4 text-sm font-semibold text-center transition-colors duration-200 flex items-center justify-center gap-2 ${mode === "file" ? "bg-indigo-50/50 text-indigo-600 border-b-2 border-indigo-600" : "text-slate-500 hover:text-indigo-600 hover:bg-slate-50"
              }`}
          >
            <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12" /></svg>
            Upload / Camera
          </button>
          <button
            type="button"
            onClick={() => { setMode("manual"); stopCamera(); }}
            className={`flex-1 py-4 text-sm font-semibold text-center transition-colors duration-200 flex items-center justify-center gap-2 ${mode === "manual" ? "bg-indigo-50/50 text-indigo-600 border-b-2 border-indigo-600" : "text-slate-500 hover:text-indigo-600 hover:bg-slate-50"
              }`}
          >
            <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z" /></svg>
            Manual Entry
          </button>
        </div>

        <form onSubmit={uploadBill} className="p-8 space-y-6">
          {mode === "file" && (
            <div className="space-y-6 animate-in fade-in duration-300">
              {/* Camera View */}
              {showCamera ? (
                <div className="relative bg-black rounded-xl overflow-hidden aspect-video flex items-center justify-center group z-30">
                  <video
                    autoPlay
                    muted
                    playsInline
                    ref={(video) => {
                      if (video && cameraStream) video.srcObject = cameraStream;
                    }}
                    className="w-full h-full object-cover"
                  />
                  <div className="absolute bottom-6 flex gap-4">
                    <button
                      type="button"
                      onClick={(e) => { e.stopPropagation(); capturePhoto(); }}
                      className="bg-white text-black rounded-full px-6 py-2 font-bold hover:scale-105 transition-transform flex items-center gap-2 shadow-lg z-40"
                    >
                      <div className="w-4 h-4 rounded-full bg-red-500 border-2 border-white"></div>
                      Capture
                    </button>
                    <button
                      type="button"
                      onClick={(e) => { e.stopPropagation(); stopCamera(); }}
                      className="bg-black/50 text-white backdrop-blur-md rounded-full px-4 py-2 font-medium hover:bg-black/70 transition-colors z-40"
                    >
                      Cancel
                    </button>
                  </div>
                </div>
              ) : (
                <div className="relative border-2 border-dashed border-slate-300 rounded-xl p-12 text-center hover:bg-slate-50 transition-colors group">
                  {!capturedFile && (
                    <input
                      type="file"
                      name="file"
                      accept="image/*,.pdf"
                      // If we have a captured file, input is not strictly required visually but form needs logic
                      required={!capturedFile}
                      className="absolute inset-0 w-full h-full opacity-0 cursor-pointer z-0"
                      onChange={(e) => {
                        setCapturedFile(null); // Clear any camera capture
                        setFileName(e.target.files?.[0]?.name || null);
                      }}
                    />
                  )}

                  <div className="flex flex-col items-center relative z-10 pointer-events-none">
                    {capturedFile ? (
                      <div className="w-full relative aspect-video bg-slate-900 rounded-lg overflow-hidden mb-4 group-hover:scale-[1.02] transition-transform pointer-events-auto">
                        <img src={URL.createObjectURL(capturedFile)} alt="Preview" className="w-full h-full object-contain" />
                        <button
                          type="button"
                          onClick={(e) => { e.stopPropagation(); setCapturedFile(null); setFileName(null); }}
                          className="absolute top-2 right-2 bg-black/50 text-white p-1 rounded-full hover:bg-red-500 transition-colors z-20"
                        >
                          <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M6 18L18 6M6 6l12 12" /></svg>
                        </button>
                      </div>
                    ) : (
                      <div className="w-12 h-12 bg-indigo-100 text-indigo-600 rounded-full flex items-center justify-center mb-4 group-hover:scale-110 transition-transform duration-200">
                        <svg className="w-6 h-6" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4" /></svg>
                      </div>
                    )}

                    <h3 className="text-lg font-medium text-slate-900">
                      {capturedFile ? "Photo Captured" : (fileName ? fileName : "Click to Upload or Drag & Drop")}
                    </h3>
                    <p className="text-slate-500 text-sm mt-1 mb-4">{capturedFile || fileName ? 'Ready to analyze' : 'PDF, PNG, JPG up to 10MB'}</p>

                    {!capturedFile && !fileName && (
                      <div className="relative z-20 pointer-events-auto">
                        <span className="text-slate-400 text-xs uppercase tracking-wider font-semibold mb-3 block pointer-events-none">- OR -</span>
                        <button
                          type="button"
                          onClick={(e) => { e.preventDefault(); e.stopPropagation(); startCamera(); }}
                          className="px-5 py-2 bg-white border border-indigo-200 text-indigo-600 rounded-full text-sm font-semibold hover:bg-indigo-50 hover:border-indigo-300 transition-all flex items-center gap-2 mx-auto shadow-sm"
                        >
                          <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M3 9a2 2 0 012-2h.93a2 2 0 001.664-.89l.812-1.22A2 2 0 0110.07 4h3.86a2 2 0 011.664.89l.812 1.22A2 2 0 0018.07 7H19a2 2 0 012 2v9a2 2 0 01-2 2H5a2 2 0 01-2-2V9z" /><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M15 13a3 3 0 11-6 0 3 3 0 016 0z" /></svg>
                          Take a Photo
                        </button>
                      </div>
                    )}
                  </div>
                </div>
              )}
            </div>
          )}

          {mode === "manual" && (
            <div className="space-y-6 animate-in fade-in duration-300">
              <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                <div className="space-y-2">
                  <label className="text-sm font-medium text-slate-700">Vendor <span className="text-red-500">*</span></label>
                  <input name="vendor" placeholder="e.g. Walmart" required className="w-full px-4 py-2 border border-slate-300 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500 outline-none transition-all" />
                </div>
                <div className="space-y-2">
                  <label htmlFor="manual_bill_date" className="text-sm font-medium text-slate-700 cursor-pointer flex items-center gap-1">
                    Bill Date <span className="text-red-500">*</span>
                    <svg className="w-4 h-4 text-slate-400" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M8 7V3m8 4V3m-9 8h10M5 21h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v12a2 2 0 002 2z" /></svg>
                  </label>
                  <input id="manual_bill_date" name="bill_date" type="date" required className="w-full px-4 py-2 border border-slate-300 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500 outline-none transition-all cursor-pointer" />
                </div>
                <div className="space-y-2">
                  <label className="text-sm font-medium text-slate-700">Payment Method <span className="text-red-500">*</span></label>
                  <div className="relative">
                    <select name="payment_method" required className="w-full px-4 py-2 border border-slate-300 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500 outline-none transition-all appearance-none bg-white">
                      <option value="">Select Method</option>
                      <option value="Credit Card">Credit Card</option>
                      <option value="Debit Card">Debit Card</option>
                      <option value="Cash">Cash</option>
                      <option value="UPI">UPI</option>
                    </select>
                    <svg className="w-4 h-4 absolute right-3 top-3.5 text-slate-400 pointer-events-none" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M19 9l-7 7-7-7" /></svg>
                  </div>
                </div>
                <div className="space-y-2">
                  <label className="text-sm font-medium text-slate-700">Category <span className="text-red-500">*</span></label>
                  <select name="category" required className="w-full px-4 py-2 border border-slate-300 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500 outline-none transition-all appearance-none bg-white">
                    <option value="">Select Category</option>
                    <option value="Food & Dining">Food & Dining</option>
                    <option value="Transportation">Transportation</option>
                    <option value="Shopping">Shopping</option>
                    <option value="Utilities">Utilities</option>
                    <option value="Health">Health</option>
                    <option value="Other">Other</option>
                  </select>
                  <div className="absolute right-3 top-2.5 pointer-events-none">
                    <svg className="w-5 h-5 text-gray-400" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="currentColor">
                      <path fillRule="evenodd" d="M5.23 7.21a.75.75 0 011.06.02L10 11.168l3.71-3.938a.75.75 0 111.08 1.04l-4.25 4.5a.75.75 0 01-1.08 0l-4.25-4.5a.75.75 0 01.02-1.06z" clipRule="evenodd" />
                    </svg>
                  </div>
                </div>
              </div>

              <div className="pt-4 border-t border-slate-100">
                <div className="flex justify-between items-center mb-4">
                  <h4 className="font-semibold text-slate-900">Bill Details <span className="text-red-500">*</span></h4>
                  <button type="button" onClick={addItem} className="text-sm font-medium text-indigo-600 hover:text-indigo-800 flex items-center gap-1">
                    <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M12 4v16m8-8H4" /></svg>
                    Add Item
                  </button>
                </div>

                <div className="space-y-3">
                  {items.length === 0 && (
                    <div className="text-center py-6 bg-slate-50 rounded-xl border border-dashed border-slate-300">
                      <span className="text-sm text-slate-400">No items added yet</span>
                    </div>
                  )}
                  {items.map((item, idx) => (
                    <div key={idx} className="flex gap-3 items-start animate-in sliding-down duration-200">
                      <input
                        placeholder="Desc"
                        required
                        value={item.description}
                        onChange={(e) => updateItem(idx, "description", e.target.value)}
                        className="flex-grow min-w-0 px-3 py-2 border border-slate-300 rounded-lg text-sm focus:ring-1 focus:ring-indigo-500 outline-none"
                      />
                      <input
                        placeholder="Qty"
                        type="number"
                        required
                        value={item.quantity}
                        onChange={(e) => updateItem(idx, "quantity", Number(e.target.value))}
                        className="w-20 px-3 py-2 border border-slate-300 rounded-lg text-sm focus:ring-1 focus:ring-indigo-500 outline-none"
                      />
                      <input
                        placeholder="Amt"
                        type="number"
                        required
                        value={item.amount}
                        onChange={(e) => updateItem(idx, "amount", Number(e.target.value))}
                        className="w-24 px-3 py-2 border border-slate-300 rounded-lg text-sm focus:ring-1 focus:ring-indigo-500 outline-none"
                      />
                      <button
                        type="button"
                        onClick={() => removeItem(idx)}
                        className="p-2 text-slate-400 hover:text-red-500 hover:bg-red-50 rounded-lg transition-colors"
                      >
                        <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M6 18L18 6M6 6l12 12" /></svg>
                      </button>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          )}

          {mode === "file" && (
            <div className="pt-2 text-center text-sm text-slate-400 italic">
              {/* redundant fields removed */}
            </div>
          )}

          {mode === "manual" && (
            <div className="grid grid-cols-1 gap-6 pt-4 border-t border-slate-100">
              <div className="space-y-2">
                <label className="text-sm font-medium text-slate-700">Total Bill Amount <span className="text-red-500">*</span></label>
                <input name="total_amount" type="number" required placeholder="0.00" className="w-full px-4 py-2 border border-slate-300 rounded-lg focus:ring-2 focus:ring-indigo-500 outline-none font-bold text-lg" />
              </div>
            </div>
          )}

          <button
            type="submit"
            disabled={isSubmitting}
            className="w-full py-3 bg-indigo-600 hover:bg-indigo-700 text-white font-bold rounded-xl shadow-lg shadow-indigo-200 transition-all hover:shadow-indigo-300 disabled:opacity-50 disabled:cursor-not-allowed flex justify-center items-center gap-2"
          >
            {isSubmitting ? (
              <>
                <div className="animate-spin rounded-full h-5 w-5 border-b-2 border-white"></div>
                Processing...
              </>
            ) : (
              mode === "file" ? "Upload & Analyze Bill" : "Save Manual Entry"
            )}
          </button>
        </form>
      </div>

      {/* ERROR MODAL */}
      {extractionError && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/60 backdrop-blur-sm animate-in fade-in duration-200">
          <div className="bg-white rounded-2xl shadow-xl max-w-sm w-full overflow-hidden text-center p-6">
            <div className="w-16 h-16 bg-red-100 rounded-full flex items-center justify-center mx-auto mb-4">
              <svg className="w-8 h-8 text-red-500" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" /></svg>
            </div>
            <h3 className="text-xl font-bold text-slate-900 mb-2">Extraction Failed</h3>
            <p className="text-slate-500 mb-6">{extractionError}</p>
            <button
              onClick={() => setExtractionError(null)}
              className="w-full py-3 bg-slate-900 text-white font-bold rounded-xl hover:bg-slate-800 transition-colors"
            >
              Okay
            </button>
          </div>
        </div>
      )}

      {/* SUCCESS MODAL */}
      {showSuccess && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/60 backdrop-blur-sm animate-in fade-in duration-200">
          <div className="bg-white rounded-2xl shadow-xl max-w-sm w-full overflow-hidden text-center p-8">
            <div className="w-20 h-20 bg-green-100 rounded-full flex items-center justify-center mx-auto mb-6 animate-in zoom-in duration-300">
              <svg className="w-10 h-10 text-green-600" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M5 13l4 4L19 7" /></svg>
            </div>
            <h3 className="text-2xl font-bold text-slate-900 mb-2">Success!</h3>
            <p className="text-slate-500 mb-8">Your bill has been confirmed and saved successfully.</p>
            <button
              onClick={() => setShowSuccess(false)}
              className="w-full py-3 bg-indigo-600 text-white font-bold rounded-xl hover:bg-indigo-700 transition-colors shadow-lg shadow-indigo-200"
            >
              Continue
            </button>
          </div>
        </div>
      )}

      {confirmationData && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/60 backdrop-blur-sm animate-in fade-in duration-200">
          <div className="bg-white rounded-2xl shadow-2xl max-w-6xl w-full h-[90vh] overflow-hidden flex flex-col md:flex-row">

            {/* LEFT: PREVIEW or TOGGLE */}
            {confirmationData.file_path && showPreview && (
              <div className="w-full md:w-1/2 bg-slate-900 flex flex-col items-center justify-center relative border-r border-slate-200">
                <button
                  onClick={() => setShowPreview(false)}
                  className="absolute top-4 right-4 bg-black/50 text-white p-2 rounded-full hover:bg-black/70 z-10"
                  title="Hide Preview"
                >
                  <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M4 16l4.586-4.586a2 2 0 012.828 0L16 16m-2-2l1.586-1.586a2 2 0 012.828 0L20 14m-6-6h.01M6 20h12a2 2 0 002-2V6a2 2 0 00-2-2H6a2 2 0 00-2 2v12a2 2 0 002 2z" /></svg>
                </button>
                {/* Display PDF or Image based on file type */}
                {confirmationData.file_path?.toLowerCase().endsWith('.pdf') ? (
                  <iframe
                    src={`/api/download?path=${encodeURIComponent(confirmationData.file_path)}&preview=true`}
                    className="w-full h-full"
                    title="Bill Preview"
                  />
                ) : (
                  <img
                    src={`/api/download?path=${encodeURIComponent(confirmationData.file_path)}&preview=true`}
                    alt="Bill Preview"
                    className="max-w-full max-h-full object-contain"
                    onError={(e) => (e.currentTarget.src = "")} // Fallback if local path fails directly
                  />
                )}
                <div className="absolute bottom-4 text-white text-xs bg-black/40 px-3 py-1 rounded-full">
                  Original Bill
                </div>
              </div>
            )}

            {/* RIGHT: FORM */}
            <div className={`flex-1 flex flex-col h-full bg-white transition-all duration-300 ${showPreview ? "md:w-1/2" : "w-full"}`}>
              <div className="p-6 border-b border-slate-100 flex justify-between items-center bg-amber-50/50 flex-shrink-0">
                <div className="flex items-center gap-3">
                  {!showPreview && confirmationData.file_path && (
                    <button
                      onClick={() => setShowPreview(true)}
                      className="bg-indigo-50 text-indigo-600 p-2 rounded-lg hover:bg-indigo-100 transition-colors"
                      title="Show Preview"
                    >
                      <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" /><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z" /></svg>
                    </button>
                  )}
                  <div>
                    <h2 className="text-xl font-bold text-slate-900 flex items-center gap-2">
                      <span className="text-amber-500">⚠</span> Incomplete Details
                    </h2>
                    <p className="text-sm text-slate-500 mt-1">Please verify the extracted information.</p>
                  </div>
                </div>
                <button onClick={() => setConfirmationData(null)} className="text-slate-400 hover:text-slate-600 transition-colors">
                  <svg className="w-6 h-6" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M6 18L18 6M6 6l12 12" /></svg>
                </button>
              </div>

              <div className="p-6 overflow-y-auto space-y-6 flex-grow">

                {/* FIELDS GRID */}
                <div>
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-5">
                    <div className="space-y-1">
                      <label className="text-sm font-medium text-slate-700">Vendor</label>
                      <input
                        value={editedFields.vendor || ""}
                        onChange={(e) => handleFieldChange("vendor", e.target.value)}
                        className={`w-full px-3 py-2 border rounded-lg text-sm outline-none focus:ring-2 focus:ring-indigo-500 ${errors.vendor ? "border-red-400 bg-red-50 focus:ring-red-200" : "border-slate-300"}`}
                        placeholder="Vendor Name"
                      />
                      {errors.vendor && <p className="text-xs text-red-500 font-medium">{errors.vendor}</p>}
                    </div>

                    <div className="space-y-1">
                      <label htmlFor="modal_bill_date" className="text-sm font-medium text-slate-700 cursor-pointer flex items-center gap-1">
                        Bill Date
                        <svg className="w-3 h-3 text-slate-400" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M8 7V3m8 4V3m-9 8h10M5 21h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v12a2 2 0 002 2z" /></svg>
                      </label>
                      <input
                        id="modal_bill_date"
                        type="date"
                        // Handle date conversion simply for display
                        value={editedFields.bill_date ? (editedFields.bill_date.includes('T') ? editedFields.bill_date.split('T')[0] : editedFields.bill_date) : ""}
                        onChange={(e) => handleFieldChange("bill_date", e.target.value)}
                        className={`w-full px-3 py-2 border rounded-lg text-sm outline-none focus:ring-2 focus:ring-indigo-500 cursor-pointer ${errors.bill_date ? "border-red-400 bg-red-50 focus:ring-red-200" : "border-slate-300"}`}
                      />
                      {errors.bill_date && <p className="text-xs text-red-500 font-medium">{errors.bill_date}</p>}
                    </div>

                    <div className="space-y-1">
                      <label className="text-sm font-medium text-slate-700">Total Amount</label>
                      <div className="relative">
                        <span className="absolute left-3 top-2 text-slate-400">₹</span>
                        <input
                          type="number"
                          value={editedFields.total_amount || ""}
                          onChange={(e) => handleFieldChange("total_amount", Number(e.target.value))}
                          className={`w-full pl-7 pr-3 py-2 border rounded-lg text-sm outline-none focus:ring-2 focus:ring-indigo-500 ${errors.total_amount ? "border-red-400 bg-red-50 focus:ring-red-200" : "border-slate-300"}`}
                          placeholder="0.00"
                        />
                      </div>
                      {errors.total_amount && <p className="text-xs text-red-500 font-medium">{errors.total_amount}</p>}
                    </div>

                    <div className="space-y-1">
                      <label className="text-sm font-medium text-slate-700">Payment Method</label>
                      <select
                        value={editedFields.payment_method || ""}
                        onChange={(e) => handleFieldChange("payment_method", e.target.value)}
                        className={`w-full px-3 py-2 border rounded-lg text-sm outline-none focus:ring-2 focus:ring-indigo-500 bg-white ${errors.payment_method ? "border-red-400 bg-red-50 focus:ring-red-200" : "border-slate-300"}`}
                      >
                        <option value="">Select Method</option>
                        <option value="Credit Card">Credit Card</option>
                        <option value="Debit Card">Debit Card</option>
                        <option value="Cash">Cash</option>
                        <option value="UPI">UPI</option>
                      </select>
                      {errors.payment_method && <p className="text-xs text-red-500 font-medium">{errors.payment_method}</p>}
                    </div>

                    <div className="space-y-1 md:col-span-2">
                      <label className="text-sm font-medium text-slate-700">Category</label>
                      <select
                        value={editedFields.category || ""}
                        onChange={(e) => handleFieldChange("category", e.target.value)}
                        className={`w-full px-3 py-2 border rounded-lg text-sm bg-white focus:ring-2 focus:ring-indigo-500 outline-none ${errors.category ? "border-red-400 bg-red-50" : "border-slate-300"}`}
                      >
                        <option value="">Select Category</option>
                        <option value="Food & Dining">Food & Dining</option>
                        <option value="Transportation">Transportation</option>
                        <option value="Shopping">Shopping</option>
                        <option value="Utilities">Utilities</option>
                        <option value="Health">Health</option>
                        <option value="Other">Other</option>
                      </select>
                    </div>
                  </div>
                </div>

                {/* ITEMS SECTION */}
                <div>
                  <div className="flex justify-between items-center mb-3">
                    <h3 className="text-xs font-bold text-slate-500 uppercase tracking-wider">Bill Details</h3>
                    <button onClick={addModalItem} className="text-xs font-bold text-indigo-600 hover:text-indigo-800 bg-indigo-50 px-3 py-1.5 rounded-full transition-colors">+ Add Item</button>
                  </div>

                  {errors.items && <p className="text-xs text-red-500 font-medium mb-2">{errors.items}</p>}

                  <div className="border border-slate-200 rounded-xl overflow-hidden shadow-sm">
                    <table className="min-w-full divide-y divide-slate-200">
                      <thead className="bg-slate-50">
                        <tr>
                          <th className="px-3 py-2 text-left text-xs font-medium text-slate-500 uppercase">Desc</th>
                          <th className="px-3 py-2 text-right text-xs font-medium text-slate-500 uppercase w-20">Qty</th>
                          <th className="px-3 py-2 text-right text-xs font-medium text-slate-500 uppercase w-24">Amt</th>
                          <th className="w-10"></th>
                        </tr>
                      </thead>
                      <tbody className="divide-y divide-slate-200 bg-white">
                        {(!editedFields.items || editedFields.items.length === 0) && (
                          <tr>
                            <td colSpan={4} className="px-4 py-8 text-center text-sm text-slate-400 italic bg-slate-50/50">
                              No items found. Add items to track individual expenses.
                            </td>
                          </tr>
                        )}
                        {editedFields.items?.map((item: any, idx: number) => (
                          <tr key={idx} className="group hover:bg-slate-50 transition-colors">
                            <td className="px-3 py-2">
                              <input
                                value={item.description || ""}
                                onChange={(e) => updateModalItem(idx, "description", e.target.value)}
                                className="w-full px-2 py-1 border-b border-transparent hover:border-slate-300 focus:border-indigo-500 bg-transparent text-sm outline-none transition-colors"
                                placeholder="Item name"
                              />
                            </td>
                            <td className="px-3 py-2">
                              <input
                                type="number"
                                value={item.quantity || ""}
                                onChange={(e) => updateModalItem(idx, "quantity", Number(e.target.value))}
                                className="w-full px-2 py-1 border-b border-transparent hover:border-slate-300 focus:border-indigo-500 bg-transparent text-sm text-right outline-none transition-colors"
                              />
                            </td>
                            <td className="px-3 py-2">
                              <input
                                type="number"
                                value={item.amount || ""}
                                onChange={(e) => updateModalItem(idx, "amount", Number(e.target.value))}
                                className="w-full px-2 py-1 border-b border-transparent hover:border-slate-300 focus:border-indigo-500 bg-transparent text-sm text-right outline-none transition-colors"
                              />
                            </td>
                            <td className="px-2 py-2 text-center opacity-0 group-hover:opacity-100 transition-opacity">
                              <button onClick={() => removeModalItem(idx)} className="text-slate-400 hover:text-red-500 transition-colors">
                                <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M6 18L18 6M6 6l12 12" /></svg>
                              </button>
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </div>

              </div>

              <div className="p-6 border-t border-slate-100 flex justify-end gap-3 bg-slate-50 flex-shrink-0">
                <button
                  onClick={() => setConfirmationData(null)}
                  className="px-5 py-2.5 text-slate-600 font-medium hover:bg-white hover:shadow-sm rounded-lg transition-all border border-transparent hover:border-slate-200"
                >
                  Cancel
                </button>
                <button
                  onClick={handleConfirmSave}
                  className="px-6 py-2.5 bg-indigo-600 hover:bg-indigo-700 text-white font-bold rounded-lg shadow-md shadow-indigo-200 hover:shadow-indigo-300 transition-all flex items-center gap-2 transform active:scale-95"
                >
                  {isSubmitting ? (
                    <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white"></div>
                  ) : (
                    <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M5 13l4 4L19 7" /></svg>
                  )}
                  Confirm & Save
                </button>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
