import { useState } from "react";

function App() {
  const [file, setFile] = useState(null);
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(false);

  const handleFileChange = (e) => {
    setFile(e.target.files[0]);
    setData(null);
  };

  const handleUpload = async () => {
    if (!file) return alert("Dosya seçin!");

    setLoading(true);
    const formData = new FormData();
    formData.append("file", file);

    try {
      const res = await fetch("http://127.0.0.1:8000/api/invoices/extract", {
        method: "POST",
        body: formData,
      });

      if (!res.ok) throw new Error("Sunucu hatası");
      const json = await res.json();
      setData(json);
    } catch (err) {
      alert(err.message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div style={{ padding: "2rem", fontFamily: "Arial" }}>
      <h1>E-Fatura OCR</h1>
      <input type="file" onChange={handleFileChange} />
      <button onClick={handleUpload} disabled={loading} style={{ marginLeft: "1rem" }}>
        {loading ? "Yükleniyor..." : "Yükle ve Analiz Et"}
      </button>

      {data && (
        <div style={{ marginTop: "2rem" }}>
          <h2>Çıkarılan Alanlar</h2>
          <table border="1" cellPadding="5">
            <tbody>
              {Object.entries(data.fields).map(([k, v]) => (
                <tr key={k}>
                  <td>{k}</td>
                  <td>{v}</td>
                </tr>
              ))}
            </tbody>
          </table>

          <h3>XML Dosyaları</h3>
          <ul>
            <li>
              <a href={`http://127.0.0.1:8000${data.single_xml}`} target="_blank">
                Tekil XML
              </a>
            </li>
            <li>
              <a href={`http://127.0.0.1:8000${data.master_xml}`} target="_blank">
                Master XML
              </a>
            </li>
          </ul>
        </div>
      )}
    </div>
  );
}

export default App;
