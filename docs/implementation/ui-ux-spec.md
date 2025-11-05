# UI/UX Specification

## Design Principles

1. **No-code first**: Users should never need to write code or understand technical concepts
2. **Visual clarity**: Agent relationships should be immediately understandable
3. **Progressive disclosure**: Show simple options first, advanced options on demand
4. **Real-time feedback**: Users should see immediate visual feedback for all actions
5. **Forgiving interface**: Easy to undo mistakes, clear error messages

## Main Layout

```
┌─────────────────────────────────────────────────────────────┐
│  Header: Logo, Project Name, Save/Load buttons              │
├─────────────────────────────────────────────────────────────┤
│  ┌──────────────────────┐  ┌─────────────────────────────┐ │
│  │                      │  │  Agent Drawer               │ │
│  │                      │  │  (when agent selected)      │ │
│  │   Agent Canvas       │  │                             │ │
│  │   (Main workspace)   │  │  - Name & Role              │ │
│  │                      │  │  - System Prompt Editor     │ │
│  │  [Nodes & Edges]     │  │  - Tools Selection         │ │
│  │                      │  │  - Parameters              │ │
│  │                      │  │  - Test Prompt Button      │ │
│  └──────────────────────┘  └─────────────────────────────┘ │
├─────────────────────────────────────────────────────────────┤
│  Runs Console (collapsible, shows during execution)         │
│  - Execution controls, live logs, outputs                   │
└─────────────────────────────────────────────────────────────┘
```

## Agent Canvas

### Visual Elements

**Agent Nodes**
- Circular or rounded rectangle shape
- Display: Agent name (large), role (small subtitle)
- Color coding by role (optional)
- Connection handles:
  - **Output handle**: Top or right side (parent connections)
  - **Input handle**: Bottom or left side (child connections)
- Selection state: Border highlight, drawer opens
- Hover state: Subtle shadow, tooltip with quick info

**Connections (Edges)**
- Curved lines between nodes
- Arrow pointing from parent to child
- Color: Neutral gray (can be colored by status during execution)
- Hover: Show connection details
- Click: Delete connection (with confirmation)

**Canvas Controls**
- Zoom in/out buttons
- Fit to view button
- Minimap (collapsible)
- Grid background (optional, toggleable)

### Interactions

**Add Agent**
1. Click "+" button (floating action button or toolbar)
2. Modal opens with template selection
3. User selects template or "Blank Agent"
4. New node appears at center of viewport
5. Node is automatically selected (drawer opens)

**Connect Agents**
1. Hover over parent node's output handle
2. Click and drag
3. Connection line follows cursor
4. Drop on child node's input handle
5. Connection created (visual feedback: animation)

**Delete Connection**
1. Click on edge
2. Edge highlights
3. Delete button appears or context menu
4. Confirm deletion

**Select Agent**
1. Click on node
2. Node highlights, drawer opens
3. Node details shown in drawer

**Move Node**
1. Click and drag node
2. Node moves, connections update dynamically
3. Position saved on release

**Delete Agent**
1. Select agent node
2. Press Delete key or use context menu
3. Confirmation dialog (warns if agent has children)
4. Agent and its connections removed

### Context Menu (Right-click on node)

- Edit Agent
- Duplicate Agent
- Delete Agent
- Convert to Template
- View Children
- Detach from Parent

## Agent Drawer

### Layout

Slides in from right side (or bottom on mobile). Can be dismissed by clicking outside or close button.

### Sections

**1. Basic Info**
- Name: Text input
- Role: Dropdown or text input (with suggestions)
- Quick actions: Test Prompt, Duplicate, Delete

**2. System Prompt**
- Large textarea (monospace font optional)
- Character count
- Formatting hints (optional markdown preview)
- Placeholder: "Describe this agent's role, capabilities, and behavior..."
- Save button (auto-saves on blur)

**3. Tools**
- Checkbox list of available tools
- Search/filter box
- Tool descriptions on hover
- "Add Custom Tool" button (future)

**4. Parameters**
- Temperature: Slider (0-1) with value display
- Max Tokens: Number input with presets
- Model: Dropdown (gemini-2.5-flash, gemini-2.5-pro)
- Safety Settings: Expandable section (future)

**5. Relationships**
- Parent Agent: Dropdown (or "None")
- Children: List of child agents (clickable, navigates to child)
- "Add Child" button (opens template selection)

### Actions

- **Save**: Updates agent, closes drawer if no errors
- **Revert**: Discards changes
- **Test Prompt**: Opens test modal, runs single-agent execution
- **Delete**: Confirms and deletes agent

## Runs Console

### Collapsible Panel

- Default: Collapsed/minimized
- Expands when run starts
- Can be manually expanded/collapsed

### Sections

**1. Controls**
- Start Run button (disabled if no root agent selected)
- Root Agent selector (dropdown)
- Input JSON editor (collapsible)
- Stop button (during execution)

**2. Execution Status**
- Status badge: Pending, Running, Completed, Failed
- Progress indicator (if possible)
- Runtime: "Running for 2m 30s"

**3. Live Logs**
- Scrollable log panel
- Auto-scrolls to bottom
- Filter by agent (dropdown)
- Log levels: Info (gray), Warning (yellow), Error (red)
- Timestamp for each log entry

**4. Outputs**
- Tabbed by agent or tree view
- Expandable sections per agent
- Copy button for each output
- Export all button

**5. Actions**
- Rerun with same inputs
- Export transcript (JSON/text)
- Clear logs

## Templates & Tools Library

### Modal/Drawer

Accessible from toolbar or "+" button dropdown.

### Templates Tab

**Layout**
- Grid or list view
- Search/filter
- Categories: All, Product, Research, Design, Engineering, QA

**Template Card**
- Name
- Role badge
- Description
- Preview of system prompt (truncated)
- "Use Template" button

**Actions**
- Create from template
- View template details
- Save current agent as template (future)

### Tools Tab

**Layout**
- List with descriptions
- Search/filter
- Categories: Web, File, Data, Analysis

**Tool Card**
- Name
- Description
- Parameters preview
- "Add to Agent" button (if agent selected)

## Responsive Design

### Mobile (< 768px)

- Canvas: Full width, pan/zoom gestures
- Drawer: Full-screen modal instead of slide-in
- Minimap: Hidden by default
- Toolbar: Bottom navigation bar

### Tablet (768px - 1024px)

- Canvas: 70% width
- Drawer: 30% width slide-in
- Minimap: Smaller, bottom-right

### Desktop (> 1024px)

- Canvas: 75% width
- Drawer: 25% width slide-in
- All features visible

## Accessibility

- Keyboard navigation: Tab through controls, Enter to activate
- Screen reader support: ARIA labels on all interactive elements
- High contrast mode: Respects system preferences
- Focus indicators: Clear focus states on all interactive elements
- Tooltips: All icons have descriptive text

## Error States

### Validation Errors

- Inline errors below form fields
- Red border on invalid inputs
- Error message clearly explains issue
- "Fix" button links to problematic field

### Network Errors

- Toast notification for failed requests
- Retry button
- Offline indicator

### Execution Errors

- Error highlighted in logs
- Error message in runs console
- Option to retry failed node
- Export error details

## Loading States

- Skeleton loaders for agent list
- Spinner for API calls
- Progress bar for long-running operations
- Optimistic UI updates (immediate feedback, rollback on error)

