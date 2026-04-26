import sys
import re
import os

from pdfrw import PdfWriter
from pdfrw.objects.pdfname import PdfName
from pdfrw.objects.pdfstring import PdfString
from pdfrw.objects.pdfdict import PdfDict
from pdfrw.objects.pdfarray import PdfArray

import binascii

def make_js_action(js):
    action = PdfDict()
    action.S = PdfName.JavaScript
    action.JS = PdfString.encode(js)
    return action

def make_field(name, x, y, width, height, r, g, b, value="", field_type="text", hidden=False, multiline=False, text_color="0 0 0"):
    annot = PdfDict()
    annot.Type = PdfName.Annot
    annot.Subtype = PdfName.Widget
    
    if field_type == "button":
        annot.FT = PdfName.Btn
        annot.Ff = 65536 # Pushbutton
    else:
        annot.FT = PdfName.Tx
        flags = 0
        if multiline:
            flags |= 4096 # Multiline
        annot.Ff = flags
        
    annot_flags = 4 # Print
    if hidden:
        annot_flags |= 2 # Hidden
    annot.F = annot_flags

    annot.Rect = PdfArray([x, y, x + width, y + height])
    annot.T = PdfString.encode(name)
    if value:
        annot.V = PdfString.encode(str(value))

    # Appearance
    annot.AP = PdfDict()
    ap = annot.AP.N = PdfDict()
    ap.Type = PdfName.XObject
    ap.Subtype = PdfName.Form
    ap.FormType = 1
    ap.BBox = PdfArray([0, 0, width, height])
    ap.Matrix = PdfArray([1.0, 0.0, 0.0, 1.0, 0.0, 0.0])
    
    if field_type == "button":
        text_x = max((width - len(value) * 6) / 2, 5)
        text_y = height / 2 - 4
        ap.stream = f"""
        {r} {g} {b} rg
        0 0 {width} {height} re f
        {text_color} rg
        BT
        /F1 12 Tf
        {text_x} {text_y} Td
        ({value}) Tj
        ET
        """
    else:
        annot.DA = PdfString.encode(f"/F1 12 Tf {text_color} rg")
        ap.stream = f"""
        {r} {g} {b} rg
        0 0 {width} {height} re f
        {text_color} rg
        BT
        /F1 12 Tf
        5 {height/2 - 4} Td
        ({value}) Tj
        ET
        """

    annot.MK = PdfDict()
    annot.MK.BG = PdfArray([r, g, b])
    if field_type == "button":
        annot.MK.CA = PdfString.encode(str(value))

    return annot

def make_page(fields):
    page = PdfDict()
    page.Type = PdfName.Page
    page.MediaBox = PdfArray([0, 0, 612, 792])
    
    page.Resources = PdfDict()
    page.Resources.Font = PdfDict()
    page.Resources.Font.F1 = PdfDict()
    page.Resources.Font.F1.Type = PdfName.Font
    page.Resources.Font.F1.Subtype = PdfName.Type1
    page.Resources.Font.F1.BaseFont = PdfName.Helvetica

    page.Contents = PdfDict()
    page.Contents.stream = """
    BT
    0.1 0.1 0.1 rg
    /F1 20 Tf
    30 750 Td (MicroGPT) Tj
    0.4 0.4 0.4 rg
    /F1 12 Tf
    100 0 Td (Run a Transformer Language Model inside Adobe Acrobat Reader!) Tj
    ET
    """
    
    page.Annots = PdfArray(fields)
    return page

def main():
    with open("src/random.js", "r", encoding="utf-8") as f:
        random_js = f.read()
    with open("src/microgpt.js", "r", encoding="utf-8") as f:
        microgpt_js = f.read()

    input_text = ""
    if os.path.exists("reference/input.txt"):
        with open("reference/input.txt", "r", encoding="utf-8") as f:
            input_text = f.read()[:5000]

    random_js = random_js.replace("export default { seed, random, gauss, shuffle, choices };", "")
    random_js += "\nvar rand_obj = { seed: seed, random: random, gauss: gauss, shuffle: shuffle, choices: choices };\n"

    microgpt_js = re.sub(r"import .*?;\n", "", microgpt_js)
    
    js_code = f"""
        {random_js}

        var global_state = {{
            output_buffer: "",
            current_step: 0,
            num_steps_val: 0,
            docs: [],
            char_to_id: null,
            BOS: null,
            vocab_size: 0,
            n_layer: 0,
            block_size: 0,
            gpt: null,
            softmax: null,
            uchars: null,
            learning_rate: 0.01,
            beta1: 0.85,
            beta2: 0.99,
            eps_adam: 1e-8,
            m_buf: null,
            v_buf: null,
            params: null,
            output_lines: []
        }};

        function print_out(msg) {{
            global_state.output_lines.push(msg);
            if (global_state.output_lines.length > 28) {{
                global_state.output_lines.shift();
            }}
            global_state.output_buffer = global_state.output_lines.join("\\n");
        }}
        
        function flush_output() {{
            var f = this.getField("output");
            if (f) f.value = global_state.output_buffer;
        }}

        function showUI(mode) {{
            var VISIBLE = 0;
            var HIDDEN = 1;
            var fields = ["n_embd", "n_head", "n_layer", "block_size", "learning_rate", "num_steps", "temperature", "btn_train", "btn_infer", "dataset", "btn_submit", "btn_back", "output", "lbl_n_embd", "lbl_n_head", "lbl_n_layer", "lbl_block_size", "lbl_learning_rate", "lbl_num_steps", "lbl_temperature"];
            for (var i=0; i<fields.length; i++) {{
                var f = this.getField(fields[i]);
                if (f) f.display = HIDDEN;
            }}

            if (mode === "initial") {{
                var initial = ["n_embd", "n_head", "n_layer", "block_size", "learning_rate", "num_steps", "temperature", "btn_train", "lbl_n_embd", "lbl_n_head", "lbl_n_layer", "lbl_block_size", "lbl_learning_rate", "lbl_num_steps", "lbl_temperature"];
                for (var i=0; i<initial.length; i++) {{
                    var f = this.getField(initial[i]);
                    if (f) f.display = VISIBLE;
                }}
                var infer = this.getField("btn_infer");
                if (global_state.params && infer) {{
                    infer.display = VISIBLE;
                }}
            }} else if (mode === "dataset") {{
                var dataset = ["dataset", "btn_submit", "btn_back"];
                for (var i=0; i<dataset.length; i++) {{
                    var f = this.getField(dataset[i]);
                    if (f) f.display = VISIBLE;
                }}
            }} else if (mode === "training" || mode === "inference") {{
                var f = this.getField("output");
                if (f) f.display = VISIBLE;
            }}
        }}

        function startTrain() {{
            try {{
                this.showUI("dataset");
            }} catch (e) {{
                app.alert("Error in startTrain: " + e.message);
            }}
        }}

        function submitDataset() {{
            try {{
                var dataset_text = this.getField("dataset").value;
                if (!dataset_text) dataset_text = "";
                dataset_text = dataset_text.trim();
                
                if (!dataset_text) {{
                    app.alert("Please provide a dataset.");
                    this.showUI("dataset");
                    return;
                }}

                var isUrl = dataset_text.indexOf("http://") === 0 || dataset_text.indexOf("https://") === 0;
                var doc_ref = this;

                if (isUrl) {{
                    var url = dataset_text;
                    if (url.indexOf("github.com") !== -1 && url.indexOf("/blob/") !== -1) {{
                        url = url.replace("github.com", "raw.githubusercontent.com").replace("/blob/", "/");
                    }}
                    if (typeof fetch !== 'undefined') {{
                        doc_ref.showUI("training");
                        global_state.output_lines = [];
                        print_out("Fetching dataset from URL...");
                        doc_ref.flush_output();
                        
                        fetch(url)
                            .then(function(res) {{
                                if (!res.ok) throw new Error("HTTP " + res.status);
                                return res.text();
                            }})
                            .then(function(text) {{
                                _continueTraining(text, doc_ref);
                            }})
                            .catch(function(e) {{
                                app.alert("Fetch failed: " + e.message + "\\nYour PDF viewer likely blocks network requests for security. Please paste the raw text instead.");
                                doc_ref.showUI("initial");
                            }});
                        return;
                    }} else {{
                        app.alert("Network fetching is not supported in this PDF viewer. Please paste the raw text instead.");
                        return;
                    }}
                }} else {{
                    _continueTraining(dataset_text, doc_ref);
                }}
            }} catch(e) {{
                app.alert("Error in submitDataset: " + e.message);
            }}
        }}

        function _continueTraining(dataset_text, doc_ref) {{
            try {{
                const v_n_embd = parseInt(doc_ref.getField("n_embd").value);
                if (isNaN(v_n_embd) || v_n_embd <= 0) {{ app.alert("n_embd must be a positive integer."); doc_ref.showUI("initial"); return; }}
                const n_embd = v_n_embd;
                
                const v_n_head = parseInt(doc_ref.getField("n_head").value);
                if (isNaN(v_n_head) || v_n_head <= 0) {{ app.alert("n_head must be a positive integer."); doc_ref.showUI("initial"); return; }}
                const n_head = v_n_head;
                
                if (n_embd % n_head !== 0) {{ app.alert("n_embd must be divisible by n_head."); doc_ref.showUI("initial"); return; }}
                
                const v_n_layer = parseInt(doc_ref.getField("n_layer").value);
                if (isNaN(v_n_layer) || v_n_layer <= 0) {{ app.alert("n_layer must be a positive integer."); doc_ref.showUI("initial"); return; }}
                const n_layer = v_n_layer;
                
                const v_block_size = parseInt(doc_ref.getField("block_size").value);
                if (isNaN(v_block_size) || v_block_size <= 0) {{ app.alert("block_size must be a positive integer."); doc_ref.showUI("initial"); return; }}
                const block_size = v_block_size;
                
                const v_learning_rate = parseFloat(doc_ref.getField("learning_rate").value);
                if (isNaN(v_learning_rate) || v_learning_rate <= 0) {{ app.alert("learning_rate must be a positive float."); doc_ref.showUI("initial"); return; }}
                const learning_rate = v_learning_rate;
                
                const v_num_steps = parseInt(doc_ref.getField("num_steps").value);
                if (isNaN(v_num_steps) || v_num_steps <= 0) {{ app.alert("num_steps must be a positive integer."); doc_ref.showUI("initial"); return; }}
                
                doc_ref.showUI("training");
                global_state.output_lines = [];
                print_out("Starting training...");
                doc_ref.flush_output();
                
                rand_obj.seed(42);

                var docs = dataset_text.split('\\n').map(function(l) {{ return l.trim(); }}).filter(function(l) {{ return l.length > 0; }});
                rand_obj.shuffle(docs);
                print_out("num docs: " + docs.length);
                global_state.docs = docs;

                var uchars_set = {{}};
                for (var i=0; i<docs.length; i++) {{
                    for (var j=0; j<docs[i].length; j++) {{
                        uchars_set[docs[i][j]] = true;
                    }}
                }}
                var uchars = Object.keys(uchars_set).sort();
                var char_to_id = new Map(uchars.map(function(ch, i) {{ return [ch, i]; }}));
                var BOS = uchars.length;
                var vocab_size = uchars.length + 1;
                print_out("vocab size: " + vocab_size);

                global_state.uchars = uchars;
                global_state.char_to_id = char_to_id;
                global_state.BOS = BOS;
                global_state.vocab_size = vocab_size;

                var _gen = 0;
                class Value {{
                    constructor(data, children, local_grads) {{
                        this.data = data;
                        this.grad = 0;
                        this._c0 = (children && children.length > 0) ? children[0] : null;
                        this._c1 = (children && children.length > 1) ? children[1] : null;
                        this._lg0 = (local_grads && local_grads.length > 0) ? local_grads[0] : null;
                        this._lg1 = (local_grads && local_grads.length > 1) ? local_grads[1] : null;
                        this._nch = children ? children.length : 0;
                        this._gen = 0;
                    }}
                    add(other) {{
                        if (other instanceof Value) return new Value(this.data + other.data, [this, other], [1, 1]);
                        return new Value(this.data + other, [this], [1]);
                    }}
                    mul(other) {{
                        if (other instanceof Value) return new Value(this.data * other.data, [this, other], [other.data, this.data]);
                        return new Value(this.data * other, [this], [other]);
                    }}
                    pow(other) {{ return new Value(Math.pow(this.data, other), [this], [other * Math.pow(this.data, other - 1)]); }}
                    log() {{ return new Value(Math.log(this.data), [this], [1 / this.data]); }}
                    exp() {{ const e = Math.exp(this.data); return new Value(e, [this], [e]); }}
                    relu() {{ return new Value(Math.max(0, this.data), [this], [+(this.data > 0)]); }}
                    neg() {{ return new Value(-this.data, [this], [-1]); }}
                    sub(other) {{ return this.add(other instanceof Value ? other.neg() : -other); }}
                    div(other) {{ return this.mul(other instanceof Value ? other.pow(-1) : 1 / other); }}
                    backward() {{
                        const gen = ++_gen;
                        const topo = [];
                        function build_topo(v) {{
                            if (v._gen === gen) return;
                            v._gen = gen;
                            if (v._nch >= 1) build_topo(v._c0);
                            if (v._nch === 2) build_topo(v._c1);
                            topo.push(v);
                        }}
                        build_topo(this);
                        this.grad = 1;
                        for (let i = topo.length - 1; i >= 0; --i) {{
                            const v = topo[i], g = v.grad;
                            if (v._nch >= 1) v._c0.grad += v._lg0 * g;
                            if (v._nch === 2) v._c1.grad += v._lg1 * g;
                        }}
                    }}
                }}
                global_state.Value = Value;

                const head_dim = Math.floor(n_embd / n_head);
                const scale = 1 / Math.pow(head_dim, 0.5);
                const matrix = (nout, nin, std) => Array.from({{ length: nout }}, () => Array.from({{ length: nin }}, () => new Value(rand_obj.gauss(0, std || 0.08))));
                const state_dict = {{ wte: matrix(vocab_size, n_embd), wpe: matrix(block_size, n_embd), lm_head: matrix(vocab_size, n_embd) }};
                for (let i = 0; i < n_layer; ++i) {{
                    state_dict[`layer${{i}}.attn_wq`] = matrix(n_embd, n_embd);
                    state_dict[`layer${{i}}.attn_wk`] = matrix(n_embd, n_embd);
                    state_dict[`layer${{i}}.attn_wv`] = matrix(n_embd, n_embd);
                    state_dict[`layer${{i}}.attn_wo`] = matrix(n_embd, n_embd);
                    state_dict[`layer${{i}}.mlp_fc1`] = matrix(4 * n_embd, n_embd);
                    state_dict[`layer${{i}}.mlp_fc2`] = matrix(n_embd, 4 * n_embd);
                }}
                const params = [];
                for (var key in state_dict) {{
                    var mat = state_dict[key];
                    for (var r=0; r<mat.length; r++) {{
                        for(var c=0; c<mat[r].length; c++) {{
                            params.push(mat[r][c]);
                        }}
                    }}
                }}
                print_out("num params: " + params.length);
                
                global_state.state_dict = state_dict;
                global_state.n_layer = n_layer;
                global_state.n_head = n_head;
                global_state.head_dim = head_dim;
                global_state.scale = scale;
                global_state.block_size = block_size;
                global_state.params = params;
                global_state.learning_rate = learning_rate;

                const sum = (arr) => arr.reduce((a, b) => a.add(b));
                const zip = (a, b) => a.map((ai, i) => [ai, b[i]]);

                function linear(x, w) {{
                    return w.map(wo => sum(wo.map((wi, i) => wi.mul(x[i]))));
                }}

                function softmax(logits) {{
                    const max_val = Math.max.apply(null, logits.map(v => v.data));
                    const exps = logits.map(v => v.sub(max_val).exp());
                    const total = sum(exps);
                    return exps.map(e => e.div(total));
                }}

                function rmsnorm(x) {{
                    const ms = sum(x.map(xi => xi.mul(xi))).mul(1 / x.length);
                    const s = ms.add(1e-5).pow(-0.5);
                    return x.map(xi => xi.mul(s));
                }}

                function gpt(token_id, pos_id, keys, values) {{
                    const tok_emb = state_dict['wte'][token_id];
                    const pos_emb = state_dict['wpe'][pos_id];
                    let x = zip(tok_emb, pos_emb).map(function(pair) {{ return pair[0].add(pair[1]); }});
                    x = rmsnorm(x);

                    for (let li = 0; li < n_layer; ++li) {{
                        let x_residual = x;
                        x = rmsnorm(x);
                        const q = linear(x, state_dict[`layer${{li}}.attn_wq`]);
                        const k = linear(x, state_dict[`layer${{li}}.attn_wk`]);
                        const v = linear(x, state_dict[`layer${{li}}.attn_wv`]);
                        keys[li].push(k);
                        values[li].push(v);
                        const x_attn = [];
                        for (let h = 0; h < n_head; ++h) {{
                            const hs = h * head_dim;
                            const q_h = q.slice(hs, hs + head_dim);
                            const k_h = keys[li].map(ki => ki.slice(hs, hs + head_dim));
                            const v_h = values[li].map(vi => vi.slice(hs, hs + head_dim));
                            const attn_logits = k_h.map(kt => sum(zip(q_h, kt).map(function(pair) {{ return pair[0].mul(pair[1]); }})).mul(scale));
                            const attn_weights = softmax(attn_logits);
                            for (let j = 0; j < head_dim; ++j)
                                x_attn.push(sum(attn_weights.map((aw, t) => aw.mul(v_h[t][j]))));
                        }}
                        x = linear(x_attn, state_dict[`layer${{li}}.attn_wo`]);
                        x = x.map((a, i) => a.add(x_residual[i]));
                        x_residual = x;
                        x = rmsnorm(x);
                        x = linear(x, state_dict[`layer${{li}}.mlp_fc1`]);
                        x = x.map(xi => xi.relu());
                        x = linear(x, state_dict[`layer${{li}}.mlp_fc2`]);
                        x = x.map((a, i) => a.add(x_residual[i]));
                    }}
                    return linear(x, state_dict['lm_head']);
                }}

                global_state.gpt = gpt;
                global_state.softmax = softmax;

                global_state.m_buf = new Float64Array(params.length);
                global_state.v_buf = new Float64Array(params.length);

                global_state.num_steps_val = v_num_steps;
                global_state.step = 0;
                var doc_ref = this;
                
                var trainStep = function() {{
                    try {{
                        var chunk_size = 5;
                        var start_step = global_state.step;
                        var end_step = Math.min(start_step + chunk_size, global_state.num_steps_val);
                        
                        for (var step = start_step; step < end_step; ++step) {{
                            const doc = global_state.docs[step % global_state.docs.length];
                            const tokens = [global_state.BOS];
                            for(var i=0; i<doc.length; i++) tokens.push(global_state.char_to_id.get(doc[i]));
                            tokens.push(global_state.BOS);
                            const n = Math.min(global_state.block_size, tokens.length - 1);

                            const keys = Array.from({{ length: global_state.n_layer }}, () => []);
                            const values = Array.from({{ length: global_state.n_layer }}, () => []);
                            const losses = [];
                            for (let pos_id = 0; pos_id < n; ++pos_id) {{
                                const token_id = tokens[pos_id], target_id = tokens[pos_id + 1];
                                const logits = global_state.gpt(token_id, pos_id, keys, values);
                                const probs = global_state.softmax(logits);
                                const loss_t = probs[target_id].log().neg();
                                losses.push(loss_t);
                            }}
                            const loss = losses.reduce((a, b) => a.add(b)).mul(1 / n);

                            loss.backward();

                            const lr_t = global_state.learning_rate * (1 - step / global_state.num_steps_val);
                            const bc1 = 1 - Math.pow(global_state.beta1, step + 1), bc2 = 1 - Math.pow(global_state.beta2, step + 1);
                            for (let i = 0; i < global_state.params.length; ++i) {{
                                const p = global_state.params[i];
                                global_state.m_buf[i] = global_state.beta1 * global_state.m_buf[i] + (1 - global_state.beta1) * p.grad;
                                global_state.v_buf[i] = global_state.beta2 * global_state.v_buf[i] + (1 - global_state.beta2) * Math.pow(p.grad, 2);
                                const m_hat = global_state.m_buf[i] / bc1;
                                const v_hat = global_state.v_buf[i] / bc2;
                                p.data -= lr_t * m_hat / (Math.sqrt(v_hat) + global_state.eps_adam);
                                p.grad = 0;
                            }}

                            if ((step+1) % 5 === 0 || step === 0 || step === global_state.num_steps_val - 1) {{
                                print_out("step " + (step+1) + " / " + global_state.num_steps_val + " | loss " + loss.data.toFixed(4));
                            }}
                        }}
                        
                        global_state.step = end_step;
                        doc_ref.flush_output();
                        
                        if (global_state.step < global_state.num_steps_val) {{
                            if (typeof setTimeout !== 'undefined') {{
                                setTimeout(trainStep, 10);
                            }} else if (typeof app !== 'undefined' && app.setTimeOut) {{
                                doc_ref.trainStep = trainStep;
                                app.setTimeOut("trainStep();", 10);
                            }} else {{
                                trainStep();
                            }}
                        }} else {{
                            print_out("Training completed!");
                            doc_ref.flush_output();
                            
                            var btn_infer = doc_ref.getField("btn_infer");
                            if (btn_infer) btn_infer.display = 0;
                            var btn_train = doc_ref.getField("btn_train");
                            if (btn_train) {{
                                btn_train.display = 0;
                                btn_train.value = "Train Again";
                            }}
                        }}
                    }} catch(e) {{
                        app.alert("Error during training step: " + e.message + " line: " + e.lineNumber + "\\n" + e.stack);
                        doc_ref.showUI("initial");
                    }}
                }};
                
                trainStep();
                
            }} catch(e) {{
                app.alert("Error during training: " + e.message + " line: " + e.lineNumber + "\\n" + e.stack);
                this.showUI("initial");
            }}
        }}

        function runInference() {{
            try {{
                if (!global_state.params) {{
                    app.alert("Please run training first!");
                    return;
                }}
                this.showUI("inference");
                
                const v_temperature = parseFloat(this.getField("temperature").value);
                if (isNaN(v_temperature) || v_temperature <= 0) {{ app.alert("temperature must be a positive float."); this.showUI("initial"); return; }}
                const temperature_val = v_temperature;
                
                global_state.output_lines = [];
                print_out("--- inference (hallucinated text) ---");
                
                const vocab_size = global_state.vocab_size;
                const BOS = global_state.BOS;
                const token_ids = Array.from({{ length: vocab_size }}, (_, i) => i);
                const n_layer = global_state.n_layer;
                const block_size = global_state.block_size;
                const gpt = global_state.gpt;
                const softmax = global_state.softmax;
                const uchars = global_state.uchars;

                for (let sample_idx = 0; sample_idx < 5; ++sample_idx) {{
                    const keys = Array.from({{ length: n_layer }}, () => []);
                    const values = Array.from({{ length: n_layer }}, () => []);
                    let token_id = BOS;
                    const sample = [];
                    for (let pos_id = 0; pos_id < block_size; ++pos_id) {{
                        const logits = gpt(token_id, pos_id, keys, values);
                        const probs = softmax(logits.map(l => l.div(temperature_val)));
                        token_id = rand_obj.choices(token_ids, probs.map(p => p.data));
                        if (token_id === BOS) break;
                        sample.push(uchars[token_id]);
                    }}
                    print_out("sample " + (sample_idx + 1) + ": " + sample.join(''));
                }}
                
                this.flush_output();

                var btn_train = this.getField("btn_train");
                if (btn_train) btn_train.display = 0;
                var btn_infer = this.getField("btn_infer");
                if (btn_infer) btn_infer.display = 0;

            }} catch(e) {{
                print_out("Error during inference: " + e.message);
                this.flush_output();
            }}
        }}
        
        function goBack() {{
            this.showUI("initial");
        }}

        // EXPORT to document global context
        this.showUI = showUI;
        this.startTrain = startTrain;
        this.submitDataset = submitDataset;
        this.runInference = runInference;
        this.goBack = goBack;
        this.flush_output = flush_output;
        this.print_out = print_out;
    """

    fields = []
    
    # Minimalistic Modern Layout
    col1_x_label = 30
    col1_x_input = 130
    col2_x_label = 280
    col2_x_input = 380
    
    params = [
        ('n_embd', '16', col1_x_label, col1_x_input, 700),
        ('n_head', '4', col2_x_label, col2_x_input, 700),
        ('n_layer', '1', col1_x_label, col1_x_input, 660),
        ('block_size', '16', col2_x_label, col2_x_input, 660),
        ('learning_rate', '0.01', col1_x_label, col1_x_input, 620),
        ('num_steps', '100', col2_x_label, col2_x_input, 620),
        ('temperature', '0.5', col1_x_label, col1_x_input, 580)
    ]
    
    for name, def_val, lbl_x, inp_x, y in params:
        lbl = make_field(
            'lbl_' + name, x=lbl_x, y=y, width=90, height=20,
            r=1.0, g=1.0, b=1.0, value=name, field_type="text", text_color="0.3 0.3 0.3"
        )
        lbl.Ff |= 1 # Readonly
        fields.append(lbl)
        
        fields.append(make_field(
            name, x=inp_x, y=y, width=100, height=20,
            r=0.96, g=0.96, b=0.96, value=def_val, field_type="text"
        ))

    btn_train = make_field(
        'btn_train', x=col1_x_label, y=530, width=120, height=35,
        r=0.1, g=0.45, b=0.85, value="Train Model", field_type="button", text_color="1 1 1"
    )
    # Using 'this' refers to the Doc object in a PDF button action
    btn_train.A = make_js_action("if (typeof startTrain !== 'undefined') startTrain(); else if (this.startTrain) this.startTrain(); else app.alert('startTrain not found');")
    fields.append(btn_train)
    
    btn_infer = make_field(
        'btn_infer', x=170, y=530, width=120, height=35,
        r=0.2, g=0.6, b=0.3, value="Inference", field_type="button", hidden=True, text_color="1 1 1"
    )
    btn_infer.A = make_js_action("if (typeof runInference !== 'undefined') runInference(); else if (this.runInference) this.runInference(); else app.alert('runInference not found');")
    fields.append(btn_infer)

    fields.append(make_field(
        'output', x=30, y=30, width=552, height=470,
        r=0.97, g=0.97, b=0.97, value="", field_type="text", hidden=True, multiline=True
    ))

    dataset_default = input_text if input_text else "Paste dataset or github URL here..."
    fields.append(make_field(
        'dataset', x=30, y=80, width=552, height=620,
        r=0.98, g=0.98, b=0.98, value=dataset_default, field_type="text", hidden=True, multiline=True
    ))
    
    btn_back = make_field(
        'btn_back', x=30, y=30, width=100, height=35,
        r=0.5, g=0.5, b=0.5, value="Cancel", field_type="button", hidden=True, text_color="1 1 1"
    )
    btn_back.A = make_js_action("if (typeof goBack !== 'undefined') goBack(); else if (this.goBack) this.goBack();")
    fields.append(btn_back)

    btn_submit = make_field(
        'btn_submit', x=462, y=30, width=120, height=35,
        r=0.1, g=0.45, b=0.85, value="Submit Dataset", field_type="button", hidden=True, text_color="1 1 1"
    )
    btn_submit.A = make_js_action("if (typeof submitDataset !== 'undefined') submitDataset(); else if (this.submitDataset) this.submitDataset();")
    fields.append(btn_submit)

    out = PdfWriter()
    out.addpage(make_page(fields))
    
    # Add AcroForm dict to tell viewers to generate appearances if missing
    if out.trailer.Root.AcroForm is None:
        from pdfrw.objects.pdfobject import PdfObject
        out.trailer.Root.AcroForm = PdfDict()
        out.trailer.Root.AcroForm.Fields = PdfArray(fields)
    
    # Document-level JS
    js_dict = PdfDict()
    js_dict.Names = PdfArray([
        PdfString.encode("init_script"),
        make_js_action(js_code)
    ])
    if out.trailer.Root.Names is None:
        out.trailer.Root.Names = PdfDict()
    out.trailer.Root.Names.JavaScript = js_dict
    
    out.write('microgpt.pdf')

if __name__ == "__main__":
    main()
