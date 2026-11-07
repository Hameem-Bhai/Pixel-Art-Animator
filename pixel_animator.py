import tkinter as tk
from tkinter import ttk, colorchooser, filedialog, messagebox, simpledialog
import json, base64, io, math, os, sys, time
from PIL import Image, ImageTk, ImageColor
import traceback

class PixelAnimator:
    def __init__(self, root):
        self.root = root
        self.root.title('Pixel Art Animator')
        self.width = 32
        self.height = 32
        self.cell_size = 16
        self.palette = ['#000000','#ffffff','#ff0000','#00ff00','#0000ff','#ffff00','#ff00ff','#00ffff','#804000','#c0c0c0','#808080','#400080','#008040','#804080','#ffa500','#8b4513']
        self.frames = []
        self.current = 0
        self.fps = 6
        self.loop = True
        self.playing = False
        self.onion = False
        self.filename = None
        self._thumb_cache = {}
        self.undo_stack = []  # list of (frame_index, pixels_snapshot)
        self.redo_stack = []  # same structure
        self._dragging = False
        self.frame_notes = []
        self.theme_bg = '#ffe6f0'  # light pink background
        self.theme_bg_dark = '#ffc2d6'  # slightly darker accent
        self.theme_border = '#ff99c2'
        self.grid_color = '#ffccd9'
        self.bg_index = 0  # background color index
        self.dirty = False
        self.recent_file_store = os.path.join(os.path.dirname(__file__), 'recent_projects.json')
        self.autosave_path = os.path.join(os.path.dirname(__file__), 'pixel_animator_autosave.json')
        self.selection = None  # {'x0','y0','x1','y1','pixels': [...], 'moving': bool}
        self._autosave_scheduled = False
        # initialize lasso before UI build/render
        self.lasso_active = False
        self.lasso_points = []
        self.root.protocol('WM_DELETE_WINDOW', self._on_close)
        self._create_default_project()
        self._build_ui()
        self._render_frame()

    def _create_default_project(self):
        pix = [0]*(self.width*self.height)
        self.frames = [pix]
        self.current = 0
        self.frame_notes = ['']
        self.bg_index = 0
        self.dirty = False

    def _build_ui(self):
        # apply pink theme styling before creating widgets
        style = ttk.Style()
        try:
            style.theme_use('clam')
        except Exception:
            pass
        style.configure('TFrame', background=self.theme_bg)
        style.configure('TLabel', background=self.theme_bg, foreground='#660033')
        style.configure('TButton', background=self.theme_bg_dark, foreground='#660033')
        style.map('TButton', background=[('active', self.theme_border)], foreground=[('disabled', '#996680')])
        self.root.configure(bg=self.theme_bg)

        left = ttk.Frame(self.root)
        left.grid(row=0,column=0,sticky='nsw')
        right = ttk.Frame(self.root)
        right.grid(row=0,column=1,sticky='nse')
        canvas_w = self.width*self.cell_size
        canvas_h = self.height*self.cell_size
        self.canvas = tk.Canvas(left,width=canvas_w,height=canvas_h,bg=self.theme_bg,highlightthickness=1,highlightbackground=self.theme_border,relief='sunken')
        self.canvas.grid(row=0,column=0,padx=8,pady=8)
        self.canvas.bind('<Button-1>',self._on_canvas_click)
        self.canvas.bind('<B1-Motion>',self._on_canvas_drag)
        self.canvas.bind('<Motion>',self._on_canvas_motion)
        self.canvas.bind('<ButtonRelease-1>', self._on_canvas_release)

        tools = ttk.Frame(right)
        tools.grid(row=0,column=0,sticky='nw')
        self.tool_var = tk.StringVar(value='pencil')
        for t in [('Pencil','pencil'),('Eraser','eraser'),('Fill','fill')]:
            rb = ttk.Radiobutton(tools,text=t[0],variable=self.tool_var,value=t[1])
            rb.pack(anchor='w',pady=2)
        # removed Lasso tool
        col_btn = ttk.Button(tools,text='Choose Color',command=self._choose_color)
        col_btn.pack(fill='x',pady=4)
        self.color_index = 2
        self.color_preview = tk.Canvas(tools,width=40,height=20,bg=self.palette[self.color_index],highlightthickness=1)
        self.color_preview.pack(pady=2)
        pal_frame = ttk.Frame(tools)
        pal_frame.pack(pady=6)
        self.pal_frame = pal_frame
        for i,c in enumerate(self.palette):
            b = tk.Button(pal_frame,bg=c,width=2,command=lambda i=i:self._select_palette(i))
            b.grid(row=i//4,column=i%4,padx=2,pady=2)
        nav = ttk.Frame(right)
        nav.grid(row=1,column=0,sticky='nw',pady=8)
        btns = [ ('New',self._new_project),('Add',self._add_frame),('Dup',self._dup_frame),('Del',self._del_frame),('Left',self._move_left),('Right',self._move_right) ]
        for t,f in btns:
            ttk.Button(nav,text=t,command=f).pack(side='left',padx=2)
        # Add Undo/Redo buttons
        ttk.Button(nav,text='Undo',command=self._undo).pack(side='left',padx=2)
        ttk.Button(nav,text='Redo',command=self._redo).pack(side='left',padx=2)
        timeline_frame = ttk.Frame(right)
        timeline_frame.grid(row=2,column=0,sticky='nw',pady=6)
        self.thumb_container = ttk.Frame(timeline_frame)
        self.thumb_container.pack()
        self._rebuild_thumbnails()
        play_frame = ttk.Frame(right)
        play_frame.grid(row=3,column=0,sticky='nw',pady=6)
        self.play_btn = ttk.Button(play_frame,text='Play',command=self._toggle_play)
        self.play_btn.pack(side='left',padx=4)
        ttk.Label(play_frame,text='FPS').pack(side='left')
        self.fps_var = tk.IntVar(value=self.fps)
        fps_spin = ttk.Spinbox(play_frame,from_=1,to=60,textvariable=self.fps_var,width=4,command=self._change_fps)
        fps_spin.pack(side='left',padx=4)
        self.loop_var = tk.BooleanVar(value=self.loop)
        ttk.Checkbutton(play_frame,text='Loop',variable=self.loop_var,command=self._toggle_loop).pack(side='left',padx=4)
        self.onion_var = tk.BooleanVar(value=self.onion)
        ttk.Checkbutton(play_frame,text='Onion',variable=self.onion_var,command=self._toggle_onion).pack(side='left',padx=4)
        io_frame = ttk.Frame(right)
        io_frame.grid(row=4,column=0,sticky='nw',pady=6)
        ttk.Button(io_frame,text='Save',command=self._save).pack(side='left',padx=4)
        ttk.Button(io_frame,text='Load',command=self._load).pack(side='left',padx=4)
        ttk.Button(io_frame,text='Export Spritesheet',command=self._export_spritesheet).pack(side='left',padx=4)
        ttk.Button(io_frame,text='Export GIF',command=self._export_gif).pack(side='left',padx=4)
        # Frame note editor
        note_frame = ttk.Frame(right)
        note_frame.grid(row=5,column=0,sticky='nw',pady=6)
        ttk.Label(note_frame,text='Frame Note:').pack(anchor='w')
        self.note_text = tk.Text(note_frame,height=3,width=40)
        self.note_text.pack()
        self.note_text.bind('<KeyRelease>',lambda e: self._update_note())
        status = ttk.Frame(self.root)
        status.grid(row=1,column=0,columnspan=2,sticky='we')
        self.status_lbl = ttk.Label(status,text='Ready')
        self.status_lbl.pack(fill='x')
        self.status_lbl.config(background=self.theme_bg, foreground='#660033')

        self.grid_var = tk.BooleanVar(value=False)
        tk.Checkbutton(tools,text='Grid',variable=self.grid_var,command=self._render_frame).pack(anchor='w',pady=2)
        ttk.Label(tools,text='Zoom').pack(anchor='w')
        self.zoom_var = tk.IntVar(value=self.cell_size)
        zoom_spin = ttk.Spinbox(tools,from_=4,to=64,increment=2,textvariable=self.zoom_var,width=5,command=self._change_zoom)
        zoom_spin.pack(anchor='w',pady=2)

        # Menu bar
        menubar = tk.Menu(self.root)
        file_menu = tk.Menu(menubar, tearoff=0)
        file_menu.add_command(label='New Paint', command=self._new_custom_project)
        file_menu.add_command(label='Open...', command=self._load)
        file_menu.add_command(label='Recent Projects...', command=self._show_recent_projects)
        file_menu.add_command(label='Open Draft', command=self._open_draft)
        file_menu.add_separator()
        file_menu.add_command(label='Save', command=self._save)
        file_menu.add_command(label='Save As...', command=self._save_as)
        file_menu.add_separator()
        file_menu.add_command(label='Export Spritesheet', command=self._export_spritesheet)
        file_menu.add_command(label='Export GIF', command=self._export_gif)
        file_menu.add_separator()
        file_menu.add_command(label='Exit', command=self._on_close)
        menubar.add_cascade(label='File', menu=file_menu)
        edit_menu = tk.Menu(menubar, tearoff=0)
        edit_menu.add_command(label='Undo', command=self._undo)
        edit_menu.add_command(label='Redo', command=self._redo)
        edit_menu.add_command(label='Clear Selection', command=self._clear_selection)
        menubar.add_cascade(label='Edit', menu=edit_menu)
        self.root.config(menu=menubar)

        # Add Select tool radio
        rb = ttk.Radiobutton(tools,text='Select',variable=self.tool_var,value='select')
        rb.pack(anchor='w',pady=2)
        # selection action buttons (remove Scale Sel)
        sel_frame = ttk.Frame(right)
        sel_frame.grid(row=6,column=0,sticky='nw')
        ttk.Button(sel_frame,text='Clear Sel',command=self._clear_selection).pack(side='left',padx=2)

    def _change_zoom(self):
        try:
            v = int(self.zoom_var.get())
            if v<4: v=4
            self.cell_size = v
            self.canvas.config(width=self.width*self.cell_size,height=self.height*self.cell_size)
            self._render_frame()
        except Exception:
            pass

    def _select_palette(self,i):
        self.color_index = i
        self.color_preview.config(bg=self.palette[i])

    def _choose_color(self):
        c = colorchooser.askcolor()[1]
        if c:
            self.palette.append(c)
            idx = len(self.palette)-1
            self._select_palette(idx)
            b = tk.Button(self.pal_frame,bg=c,width=2,command=lambda i=idx:self._select_palette(i))
            row = idx//4; col = idx%4
            b.grid(row=row,column=col,padx=2,pady=2)

    def _new_project(self):
        w = simpledialog.askinteger('New Project','Width (pixels per frame)?',initialvalue=self.width,minvalue=1,maxvalue=256)
        if w is None: return
        h = simpledialog.askinteger('New Project','Height (pixels per frame)?',initialvalue=self.height,minvalue=1,maxvalue=256)
        if h is None: return
        self.width = w
        self.height = h
        self.frames = [[0]*(self.width*self.height)]
        self.current = 0
        self.filename = None
        self._thumb_cache.clear()
        self.canvas.config(width=self.width*self.cell_size,height=self.height*self.cell_size)
        self._render_frame()
        self.status_lbl.config(text='New project created')
        self.frame_notes = ['']
        self.note_text.delete('1.0','end')

    def _coords_to_index(self,x,y):
        cx = x//self.cell_size
        cy = y//self.cell_size
        if cx<0 or cy<0 or cx>=self.width or cy>=self.height:
            return None
        return cy*self.width+cx

    def _on_canvas_motion(self,event):
        idx = self._coords_to_index(event.x,event.y)
        if idx is None:
            self.status_lbl.config(text='Ready')
            return
        cx = idx % self.width
        cy = idx // self.width
        selflag = ''
        if self.selection and self.selection['x0']<=cx<=self.selection['x1'] and self.selection['y0']<=cy<=self.selection['y1']:
            selflag = ' [in selection]'
        self.status_lbl.config(text=f'Frame {self.current+1}/{len(self.frames)} x={cx} y={cy}{selflag}')

    def _mark_dirty(self):
        self.dirty = True
        self._schedule_autosave()

    def _schedule_autosave(self):
        if self._autosave_scheduled:
            return
        self._autosave_scheduled = True
        self.root.after(2000, self._autosave)

    def _autosave(self):
        self._autosave_scheduled = False
        if not self.dirty:
            return
        try:
            data = self._serialize_project()
            with open(self.autosave_path,'w',encoding='utf8') as f:
                json.dump(data,f)
        except Exception:
            pass

    def _serialize_project(self):
        data = {'version':1,'meta':{'width':self.width,'height':self.height,'fps':self.fps,'palette':self.palette,'bg_index':self.bg_index},'frames':[]}
        for i in range(len(self.frames)):
            im = self._frame_to_image(i)
            buf = io.BytesIO(); im.save(buf,format='PNG'); b = base64.b64encode(buf.getvalue()).decode('ascii')
            note = self.frame_notes[i] if i < len(self.frame_notes) else ''
            data['frames'].append({'index':i,'png_base64':b,'note':note})
        return data

    def _save_recent(self, path):
        try:
            lst = []
            if os.path.exists(self.recent_file_store):
                with open(self.recent_file_store,'r',encoding='utf8') as f:
                    lst = json.load(f)
            lst = [p for p in lst if p!=path]
            lst.insert(0,path)
            lst = lst[:10]
            with open(self.recent_file_store,'w',encoding='utf8') as f:
                json.dump(lst,f)
        except Exception:
            pass

    def _show_recent_projects(self):
        if not os.path.exists(self.recent_file_store):
            messagebox.showinfo('Recent','No recent projects')
            return
        try:
            with open(self.recent_file_store,'r',encoding='utf8') as f:
                lst = json.load(f)
        except Exception:
            lst=[]
        if not lst:
            messagebox.showinfo('Recent','No recent projects')
            return
        top = tk.Toplevel(self.root); top.title('Recent Projects')
        lb = tk.Listbox(top,width=60,height=10)
        lb.pack(side='left',fill='both',expand=True)
        for p in lst:
            lb.insert('end',p)
        def load_sel():
            sel = lb.curselection()
            if not sel: return
            self._load_path(lb.get(sel[0]))
            top.destroy()
        ttk.Button(top,text='Open Selected',command=load_sel).pack(side='left',padx=4,pady=4)

    def _open_draft(self):
        if not os.path.exists(self.autosave_path):
            messagebox.showinfo('Draft','No draft found')
            return
        self._load_path(self.autosave_path,draft=True)

    def _on_close(self):
        if self.dirty:
            ans = messagebox.askyesnocancel('Unsaved Changes','Save before exit?')
            if ans is None:
                return
            if ans:
                self._save()
        # ensure draft saved
        if self.dirty:
            self._autosave()
        self.root.destroy()

    def _new_custom_project(self):
        w = simpledialog.askinteger('New Paint','Width?',initialvalue=self.width,minvalue=1,maxvalue=512)
        if w is None: return
        h = simpledialog.askinteger('New Paint','Height?',initialvalue=self.height,minvalue=1,maxvalue=512)
        if h is None: return
        bg = colorchooser.askcolor(title='Background Color')[1]
        if not bg: bg = '#000000'
        if bg not in self.palette:
            self.palette.append(bg)
        self.bg_index = self.palette.index(bg)
        self.width = w; self.height = h
        self.frames = [[self.bg_index]*(w*h)]
        self.frame_notes = ['']
        self.current = 0
        self.filename = None
        self._thumb_cache.clear()
        self.canvas.config(width=self.width*self.cell_size,height=self.height*self.cell_size,bg=self.theme_bg)
        self._rebuild_palette_buttons()
        self._render_frame()
        self.dirty = False
        self.status_lbl.config(text='New paint created')

    def _load(self):
        path = filedialog.askopenfilename(filetypes=[('Pixel Project','*.json')])
        if not path:
            return
        self._load_path(path)

    def _export_spritesheet(self):
        if not self.frames:
            messagebox.showinfo('Export','No frames to export')
            return
        try:
            cols = simpledialog.askinteger('Export Spritesheet','Columns?',initialvalue=max(1,min(len(self.frames), len(self.frames))),minvalue=1,maxvalue=len(self.frames))
            if cols is None:
                return
            scale = simpledialog.askinteger('Export Spritesheet','Scale (pixel size)?',initialvalue=1,minvalue=1,maxvalue=32)
            if scale is None:
                return
            pad = simpledialog.askinteger('Export Spritesheet','Padding (px between frames)?',initialvalue=0,minvalue=0,maxvalue=64)
            if pad is None:
                return
            save = filedialog.asksaveasfilename(defaultextension='.png',filetypes=[('PNG Image','*.png')])
            if not save:
                return
            n = len(self.frames)
            rows = (n + cols - 1)//cols
            fw = self.width*scale
            fh = self.height*scale
            sheet_w = cols*fw + pad*(cols-1 if cols>1 else 0)
            sheet_h = rows*fh + pad*(rows-1 if rows>1 else 0)
            sheet = Image.new('RGBA',(sheet_w, sheet_h),(255,255,255,0))
            for i in range(n):
                r = i // cols
                c = i % cols
                x = c*(fw + (pad if cols>1 else 0))
                y = r*(fh + (pad if rows>1 else 0))
                im = self._frame_to_image(i, scale=scale)
                sheet.paste(im, (x,y))
            sheet.save(save)
            messagebox.showinfo('Export','Spritesheet saved')
        except Exception as e:
            messagebox.showerror('Export Error', str(e))

    def _export_gif(self):
        if not self.frames:
            messagebox.showinfo('Export','No frames to export')
            return
        try:
            fps = simpledialog.askinteger('Export GIF','FPS?',initialvalue=self.fps,minvalue=1,maxvalue=60)
            if fps is None:
                return
            scale = simpledialog.askinteger('Export GIF','Scale (pixel size)?',initialvalue=1,minvalue=1,maxvalue=16)
            if scale is None:
                return
            save = filedialog.asksaveasfilename(defaultextension='.gif',filetypes=[('GIF','*.gif')])
            if not save:
                return
            duration = int(1000/max(1,fps))
            ims = []
            for i in range(len(self.frames)):
                im = self._frame_to_image(i, scale=scale)
                ims.append(im.convert('P', palette=Image.ADAPTIVE, colors=256))
            if not ims:
                messagebox.showinfo('Export','No frames to export')
                return
            ims[0].save(save, save_all=True, append_images=ims[1:], loop=0 if self.loop else 1, duration=duration, disposal=2)
            messagebox.showinfo('Export','GIF saved')
        except Exception as e:
            messagebox.showerror('Export Error', str(e))

    def _load_path(self,path,draft=False):
        try:
            with open(path,'r',encoding='utf8') as f: data=json.load(f)
            meta = data.get('meta',{})
            w = meta.get('width',self.width); h = meta.get('height',self.height)
            pal = meta.get('palette',self.palette)
            self.bg_index = meta.get('bg_index',0)
            loaded_fps = meta.get('fps',self.fps)
            frames=[]; notes=[]
            for fr in data.get('frames',[]):
                b64=fr.get('png_base64'); raw=base64.b64decode(b64)
                im = Image.open(io.BytesIO(raw)).convert('RGBA').resize((w,h),resample=Image.NEAREST)
                arr=list(im.getdata()); pix=[]
                for rgba in arr:
                    rgb = '#%02x%02x%02x' % (rgba[0],rgba[1],rgba[2])
                    try: idx = pal.index(rgb)
                    except: pal.append(rgb); idx=len(pal)-1
                    pix.append(idx)
                notes.append(fr.get('note',''))
                frames.append(pix)
            if frames:
                self.width=w; self.height=h; self.palette=pal; self.frames=frames; self.frame_notes=notes if len(notes)==len(frames) else ['']*len(frames)
                self.current=0; self.fps=loaded_fps; self.fps_var.set(self.fps)
                self.canvas.config(width=self.width*self.cell_size,height=self.height*self.cell_size)
                self._thumb_cache.clear(); self._rebuild_palette_buttons(); self._render_frame();
                self.filename = None if draft else path
                self.dirty = True if draft else False
                if not draft: self._save_recent(path)
                messagebox.showinfo('Loaded','Project loaded' + (' (draft)' if draft else ''))
            else:
                messagebox.showerror('Error','No frames in file')
        except Exception as e:
            messagebox.showerror('Error',str(e))

    def _save(self):
        # ...existing code replacing data building with serialize...
        if not self.filename:
            return self._save_as()
        data = self._serialize_project()
        try:
            tmp = self.filename+'.tmp'
            with open(tmp,'w',encoding='utf8') as f: json.dump(data,f)
            os.replace(tmp,self.filename)
            self.dirty = False
            self._save_recent(self.filename)
            messagebox.showinfo('Saved',f'Saved to {self.filename}')
        except Exception as e:
            messagebox.showerror('Error',str(e))

    def _save_as(self):
        path = filedialog.asksaveasfilename(defaultextension='.json',filetypes=[('Pixel Project','*.json')])
        if not path: return
        self.filename = path
        self._save()

    # Modify pixel operations to set dirty
    def _set_pixel(self,idx,color_idx):
        # ...existing code...
        self.frames[self.current][idx]=color_idx
        self._thumb_cache.pop(self.current,None)
        self._mark_dirty()

    def _del_frame(self):
        # ...existing code...
        # mark dirty
        self._mark_dirty()

    def _add_frame(self):
        # ...existing code...
        self._mark_dirty()

    def _dup_frame(self):
        # ...existing code...
        self._mark_dirty()

    def _move_left(self):
        # ...existing code...
        self._mark_dirty()

    def _move_right(self):
        # ...existing code...
        self._mark_dirty()

    def _flood_fill(self,start_idx,old_color,new_color):
        if start_idx is None:
            return
        if old_color == new_color:
            return
        frame = self.frames[self.current]
        w = self.width; h = self.height
        if frame[start_idx] != old_color:
            # nothing to fill
            return
        self._push_undo()
        stack = [start_idx]
        visited = set()
        while stack:
            i = stack.pop()
            if i in visited:
                continue
            visited.add(i)
            if frame[i] != old_color:
                continue
            frame[i] = new_color
            x = i % w; y = i // w
            if x > 0:
                stack.append(i-1)
            if x < w-1:
                stack.append(i+1)
            if y > 0:
                stack.append(i-w)
            if y < h-1:
                stack.append(i+w)
        self._thumb_cache.pop(self.current,None)
        self._mark_dirty()
        self._render_frame()

    # Selection tool handlers
    def _clear_selection(self):
        self.selection = None
        self._render_frame()

    def _handle_select_click(self,event):
        idx = self._coords_to_index(event.x,event.y)
        if idx is None: return
        cx = idx%self.width; cy=idx//self.width
        if self.selection:
            if self.selection.get('type')=='lasso':
                x0,y0 = self.selection['x0'], self.selection['y0']
                rx, ry = cx - x0, cy - y0
                poly = self.selection.get('poly_rel', [])
                inside = False
                if poly:
                    inside = self._point_in_poly(rx+0.5, ry+0.5, poly)
                if inside:
                    self.selection['moving']=True
                    self._move_offset = (rx, ry)
                    self._render_frame(); return
            else:
                if (self.selection['x0']<=cx<=self.selection['x1'] and self.selection['y0']<=cy<=self.selection['y1']):
                    self.selection['moving']=True
                    self._move_offset = (cx - self.selection['x0'], cy - self.selection['y0'])
                    self._render_frame(); return
        self.selection = {'x0':cx,'y0':cy,'x1':cx,'y1':cy,'pixels':None,'moving':False}
        self._render_frame()

    def _handle_select_drag(self,event):
        if not self.selection: return
        idx = self._coords_to_index(event.x,event.y)
        if idx is None: return
        cx = idx%self.width; cy=idx//self.width
        if self.selection['moving']:
            w = self.selection['x1']-self.selection['x0']+1
            h = self.selection['y1']-self.selection['y0']+1
            nx0 = max(0, min(self.width-w, cx - self._move_offset[0]))
            ny0 = max(0, min(self.height-h, cy - self._move_offset[1]))
            self.selection['x_preview']=nx0
            self.selection['y_preview']=ny0
        else:
            self.selection['x1']=max(self.selection['x0'],min(self.width-1,cx))
            self.selection['y1']=max(self.selection['y0'],min(self.height-1,cy))
        self._render_frame()

    def _handle_select_release(self,event):
        if not self.selection: return
        if self.selection['moving']:
            self._push_undo()
            sel=self.selection
            frame=self.frames[self.current]
            x0,y0,x1,y1 = sel['x0'],sel['y0'],sel['x1'],sel['y1']
            w=x1-x0+1; h=y1-y0+1
            nx0 = sel.get('x_preview',x0)
            ny0 = sel.get('y_preview',y0)
            if sel.get('type')=='lasso':
                mask = sel.get('mask', set())
                if sel.get('pixels') is None:
                    rect=[]
                    for yy in range(h):
                        for xx in range(w):
                            rect.append(frame[(y0+yy)*self.width + (x0+xx)])
                    sel['pixels']=rect
                for (rx,ry) in mask:
                    frame[(y0+ry)*self.width + (x0+rx)] = self.bg_index if self.bg_index < len(self.palette) else 0
                for (rx,ry) in mask:
                    val = sel['pixels'][ry*w + rx]
                    frame[(ny0+ry)*self.width + (nx0+rx)] = val
            else:
                if sel.get('pixels') is None:
                    pix=[]
                    for yy in range(h):
                        for xx in range(w):
                            pix.append(frame[(y0+yy)*self.width + (x0+xx)])
                    sel['pixels']=pix
                for yy in range(h):
                    for xx in range(w):
                        frame[(y0+yy)*self.width + (x0+xx)] = self.bg_index if self.bg_index < len(self.palette) else 0
                for yy in range(h):
                    for xx in range(w):
                        frame[(ny0+yy)*self.width + (nx0+xx)] = sel['pixels'][yy*w+xx]
            sel['x0']=nx0; sel['y0']=ny0; sel['x1']=nx0+w-1; sel['y1']=ny0+h-1
            sel.pop('x_preview',None); sel.pop('y_preview',None)
            sel['moving']=False
            self._thumb_cache.pop(self.current,None)
            self._mark_dirty()
            self._render_frame()
        else:
            sel=self.selection
            x0,y0,x1,y1 = sel['x0'],sel['y0'],sel['x1'],sel['y1']
            w=x1-x0+1; h=y1-y0+1
            frame=self.frames[self.current]
            pix=[]
            for yy in range(h):
                for xx in range(w):
                    pix.append(frame[(y0+yy)*self.width + (x0+xx)])
            sel['pixels']=pix
            self._render_frame()

    # Integrate selection tool into canvas events
    def _on_canvas_click(self,event):
        if self.tool_var.get()=='lasso':
            idx = self._coords_to_index(event.x,event.y)
            if idx is None: return
            cx = idx%self.width; cy = idx//self.width
            if not self.lasso_active:
                self._start_lasso(cx,cy)
            else:
                self._add_lasso_point(cx,cy)
            return
        if self.tool_var.get()=='select':
            self._handle_select_click(event)
            return
        # ...existing code...
        self._dragging = True
        self._push_undo()
        idx = self._coords_to_index(event.x,event.y)
        if idx is None: return
        tool = self.tool_var.get()
        if tool=='pencil':
            self._set_pixel(idx,self.color_index)
        elif tool=='eraser':
            self._set_pixel(idx,self.bg_index)
        elif tool=='fill':
            self._flood_fill(idx,self.frames[self.current][idx],self.color_index)
        self._render_frame()

    def _on_canvas_drag(self,event):
        if self.tool_var.get()=='lasso':
            if not self.lasso_active: return
            idx = self._coords_to_index(event.x,event.y)
            if idx is None: return
            cx = idx%self.width; cy = idx//self.width
            self._add_lasso_point(cx,cy)
            return
        if self.tool_var.get()=='select':
            self._handle_select_drag(event)
            return
        # ...existing code...
        idx = self._coords_to_index(event.x,event.y)
        if idx is None: return
        tool = self.tool_var.get()
        if tool=='pencil':
            self._set_pixel(idx,self.color_index)
        elif tool=='eraser':
            self._set_pixel(idx,self.bg_index)
        self._render_frame()

    def _on_canvas_release(self,event):
        if self.tool_var.get()=='lasso':
            return
        if self.tool_var.get()=='select':
            self._handle_select_release(event)
            return
        # ...existing code...
        self._dragging = False

    def _render_frame(self):
        img = self._frame_to_image(self.current)
        if self.onion_var.get():
            prev_idx = (self.current-1)%len(self.frames)
            if prev_idx!=self.current:
                prev = self._frame_to_image(prev_idx).convert('RGBA')
                overlay = prev.copy()
                alpha = overlay.split()[3].point(lambda p: p//2)
                overlay.putalpha(alpha)
                img = Image.alpha_composite(img.convert('RGBA'),overlay)
        tkimg = ImageTk.PhotoImage(img.resize((self.width*self.cell_size,self.height*self.cell_size),resample=Image.NEAREST))
        self.canvas.image = tkimg
        self.canvas.delete('all')
        self.canvas.create_image(0,0,anchor='nw',image=tkimg)
        if self.grid_var.get():
            for x in range(self.width+1):
                px = x*self.cell_size
                self.canvas.create_line(px,0,px,self.height*self.cell_size,fill=self.grid_color)
            for y in range(self.height+1):
                py = y*self.cell_size
                self.canvas.create_line(0,py,self.width*self.cell_size,py,fill=self.grid_color)
        # draw lasso path while active
        if self.lasso_active and self.lasso_points:
            pts = []
            for (gx,gy) in self.lasso_points:
                pts.append((gx*self.cell_size+ self.cell_size//2, gy*self.cell_size+ self.cell_size//2))
            for i in range(1,len(pts)):
                x1,y1 = pts[i-1]; x2,y2 = pts[i]
                self.canvas.create_line(x1,y1,x2,y2,fill='#ff4080',width=2)
        # draw selection overlay
        if self.selection:
            sel=self.selection
            if sel.get('type')=='lasso':
                x0=sel.get('x_preview',sel['x0']); y0=sel.get('y_preview',sel['y0'])
                poly = sel.get('poly_rel', [])
                if poly:
                    pts=[]
                    for (rx,ry) in poly:
                        pts.append(((x0+rx)*self.cell_size+ self.cell_size//2, (y0+ry)*self.cell_size+ self.cell_size//2))
                    for i in range(1,len(pts)):
                        x1,y1=pts[i-1]; x2,y2=pts[i]
                        self.canvas.create_line(x1,y1,x2,y2,fill='#ff4080',width=2)
            else:
                # rectangle overlay
                x0=sel.get('x_preview',sel['x0']); y0=sel.get('y_preview',sel['y0'])
                x1=sel['x1'] - sel['x0'] + x0
                y1=sel['y1'] - sel['y0'] + y0
                sx0=x0*self.cell_size; sy0=y0*self.cell_size
                sx1=(x1+1)*self.cell_size; sy1=(y1+1)*self.cell_size
                self.canvas.create_rectangle(sx0,sy0,sx1,sy1,outline='#ff4080',width=2)
        # ...existing code end render...

    def _frame_to_image(self,index,scale=1):
        pixels = self.frames[index]
        im = Image.new('RGBA',(self.width,self.height))
        data=[]
        for v in pixels:
            c = self.palette[v] if v<len(self.palette) else '#000000'
            rgb = ImageColor.getrgb(c)
            data.append((rgb[0],rgb[1],rgb[2],255))
        im.putdata(data)
        if scale!=1:
            im = im.resize((self.width*scale,self.height*scale),resample=Image.NEAREST)
        return im

    def _rebuild_thumbnails(self):
        for w in self.thumb_container.winfo_children():
            w.destroy()
        for i in range(len(self.frames)):
            img = self._thumb_cache.get(i)
            if img is None:
                im = self._frame_to_image(i,scale=4)
                img = ImageTk.PhotoImage(im)
                self._thumb_cache[i]=img
            b = tk.Button(self.thumb_container,image=img,command=lambda i=i:self._select_frame(i))
            if i==self.current:
                b.config(relief='sunken')
            b.grid(row=0,column=i,padx=2)

    def _select_frame(self,i):
        self.current=i
        self._render_frame()
        if 0 <= i < len(self.frame_notes):
            self.note_text.delete('1.0','end')
            self.note_text.insert('1.0', self.frame_notes[i])

    def _add_frame(self):
        new = [0]*(self.width*self.height)
        self.frames.insert(self.current+1,new)
        self.current+=1
        self.frame_notes.insert(self.current, '')
        # adjust note index to new current after insertion
        self.note_text.delete('1.0','end'); self.note_text.insert('1.0', self.frame_notes[self.current])
        self._push_undo()
        self._render_frame()
        self._mark_dirty()

    def _dup_frame(self):
        copy = list(self.frames[self.current])
        self.frames.insert(self.current+1,copy)
        self.current+=1
        self.frame_notes.insert(self.current, self.frame_notes[self.current-1] if self.current>0 else '')
        self.note_text.delete('1.0','end'); self.note_text.insert('1.0', self.frame_notes[self.current])
        self._push_undo()
        self._render_frame()
        self._mark_dirty()

    def _del_frame(self):
        if len(self.frames)<=1:
            messagebox.showinfo('Info','Cannot delete last frame')
            return
        if not messagebox.askyesno('Delete','Delete current frame?'):
            return
        self.frames.pop(self.current)
        if len(self.frame_notes) > self.current:
            self.frame_notes.pop(self.current)
        self.current=max(0,self.current-1)
        self._thumb_cache.clear()
        self._push_undo()
        self._render_frame()
        self.note_text.delete('1.0','end'); self.note_text.insert('1.0', self.frame_notes[self.current])
        self._mark_dirty()

    def _move_left(self):
        if self.current<=0: return
        self._push_undo()
        # swap frame and note with previous index
        idx = self.current
        self.frames[idx-1], self.frames[idx] = self.frames[idx], self.frames[idx-1]
        if idx < len(self.frame_notes) and idx-1 < len(self.frame_notes):
            self.frame_notes[idx-1], self.frame_notes[idx] = self.frame_notes[idx], self.frame_notes[idx-1]
        self.current -= 1
        self._thumb_cache.clear()
        self._render_frame()
        self._mark_dirty()

    def _move_right(self):
        if self.current>=len(self.frames)-1: return
        self._push_undo()
        idx = self.current
        self.frames[idx+1], self.frames[idx] = self.frames[idx], self.frames[idx+1]
        if idx+1 < len(self.frame_notes) and idx < len(self.frame_notes):
            self.frame_notes[idx+1], self.frame_notes[idx] = self.frame_notes[idx], self.frame_notes[idx+1]
        self.current += 1
        self._thumb_cache.clear()
        self._render_frame()
        self._mark_dirty()

    def _toggle_play(self):
        if self.playing:
            self._stop_play()
        else:
            self._start_play()

    def _start_play(self):
        self.playing = True
        self.play_btn.config(text='Stop')
        self._play_loop()

    def _stop_play(self):
        self.playing = False
        self.play_btn.config(text='Play')

    def _play_loop(self):
        if not self.playing: return
        self.current = (self.current+1)%len(self.frames)
        self._render_frame()
        delay = int(1000/max(1,self.fps_var.get()))
        if self.current==len(self.frames)-1 and not self.loop_var.get():
            self._stop_play(); return
        self.root.after(delay,self._play_loop)

    def _change_fps(self):
        try:
            v = int(self.fps_var.get())
            self.fps=v
        except:
            pass

    def _toggle_loop(self):
        self.loop = self.loop_var.get()

    def _toggle_onion(self):
        self.onion = self.onion_var.get()
        self._render_frame()

    def _update_note(self):
        i = self.current
        if 0 <= i < len(self.frame_notes):
            self.frame_notes[i] = self.note_text.get('1.0','end').rstrip('\n')
            self._mark_dirty()

    def _rebuild_palette_buttons(self):
        for w in self.pal_frame.winfo_children():
            w.destroy()
        for i,c in enumerate(self.palette):
            b = tk.Button(self.pal_frame,bg=c,width=2,command=lambda i=i:self._select_palette(i))
            b.grid(row=i//4,column=i%4,padx=2,pady=2)
        if 0 <= self.color_index < len(self.palette):
            self.color_preview.config(bg=self.palette[self.color_index])

    def _start_lasso(self, cx, cy):
        self.lasso_active = True
        self.lasso_points = [(cx,cy)]
        self.selection = None
        self._render_frame()

    def _add_lasso_point(self, cx, cy):
        if not self.lasso_active:
            return
        if not self.lasso_points or self.lasso_points[-1] != (cx,cy):
            self.lasso_points.append((cx,cy))
            self._render_frame()

    def _finish_lasso(self):
        pts = self.lasso_points
        self.lasso_active = False
        if not pts or len(pts) < 3:
            self.lasso_points = []
            self._render_frame()
            return
        if pts[0] != pts[-1]:
            pts = pts + [pts[0]]
        minx = min(p[0] for p in pts)
        maxx = max(p[0] for p in pts)
        miny = min(p[1] for p in pts)
        maxy = max(p[1] for p in pts)
        w = maxx - minx + 1
        h = maxy - miny + 1
        frame = self.frames[self.current]
        rect_pixels = []
        mask = set()
        poly = [(x-minx, y-miny) for (x,y) in pts]
        for yy in range(h):
            for xx in range(w):
                gx, gy = minx+xx, miny+yy
                val = frame[gy*self.width + gx]
                rect_pixels.append(val)
                if self._point_in_poly(xx+0.5, yy+0.5, poly):
                    mask.add((xx,yy))
        if not mask:
            self.lasso_points = []
            self._render_frame()
            return
        self.selection = {
            'type': 'lasso',
            'x0': minx, 'y0': miny, 'x1': maxx, 'y1': maxy,
            'pixels': rect_pixels,
            'mask': mask,
            'poly_rel': poly,
            'moving': False
        }
        self.lasso_points = []
        self._render_frame()

    def _point_in_poly(self, x, y, poly):
        inside = False
        n = len(poly)
        for i in range(n):
            x1,y1 = poly[i]
            x2,y2 = poly[(i+1)%n]
            if ((y1>y) != (y2>y)):
                xinters = (x2-x1)*(y-y1)/(y2-y1+1e-12) + x1
                if x < xinters:
                    inside = not inside
        return inside

    def _push_undo(self):
        if 0 <= self.current < len(self.frames):
            self.undo_stack.append((self.current, list(self.frames[self.current])))
            if len(self.undo_stack) > 200:
                self.undo_stack.pop(0)
            self.redo_stack.clear()

    def _undo(self):
        if not self.undo_stack:
            return
        frame_index, snapshot = self.undo_stack.pop()
        if 0 <= frame_index < len(self.frames):
            self.redo_stack.append((frame_index, list(self.frames[frame_index])))
            self.frames[frame_index] = snapshot
            self._thumb_cache.pop(frame_index, None)
            self.current = frame_index
            self._render_frame()

    def _redo(self):
        if not self.redo_stack:
            return
        frame_index, snapshot = self.redo_stack.pop()
        if 0 <= frame_index < len(self.frames):
            self.undo_stack.append((frame_index, list(self.frames[frame_index])))
            self.frames[frame_index] = snapshot
            self._thumb_cache.pop(frame_index, None)
            self.current = frame_index
            self._render_frame()

    def _tk_error(self, exc, val, tb):
        msg = ''.join(traceback.format_exception(exc, val, tb))
        try:
            with open(os.path.join(os.path.dirname(__file__), 'pixel_animator_error.log'), 'a', encoding='utf8') as f:
                f.write(time.strftime('%Y-%m-%d %H:%M:%S')+'\n')
                f.write(msg+'\n')
        except Exception:
            pass
        try:
            messagebox.showerror('Error', msg)
        except Exception:
            print(msg, file=sys.stderr)

if __name__=='__main__':
    print('Starting PixelAnimator...')
    try:
        root = tk.Tk()
    except Exception as e:
        print('Tkinter failed to initialize:',e); sys.exit(1)
    app = PixelAnimator(root)
    print('UI built, entering mainloop...')
    root.mainloop()
