# IDEA2APK V3 — NexGen App Builder

## Product goal
Turn a plain-language app idea into a structured project, generated source code, a previewable prototype, and an installable Android APK. Clearly distinguish a prototype, generated source package, and successfully built APK.

## V3 product principles
- Preserve existing saved projects and the current planner workflow.
- Never describe a ZIP/source package as an APK.
- Make each build traceable to its project, source revision, build run, and APK download.
- Prefer reusable templates and reliable local generation over pretending to generate arbitrary production software.
- Keep the first release usable from an Android phone and within a zero-dollar development budget.

## Main user journey
1. Create a project: name, plain-language description, target users, app category, and requested features.
2. Convert the idea into a structured blueprint with screens, data entities, actions, and validation rules.
3. Select a starter template or a supported feature set.
4. Generate source code and a project manifest.
5. Preview the generated app structure and inspect generated code.
6. Run pre-build checks (required files, package ID, app title, supported features).
7. Send the project to GitHub Actions and show the exact build status.
8. Download the APK only after the workflow confirms a successful build and APK asset/artifact exists.
9. Reopen and revise the saved project.

## V3 screens
- Dashboard: New project, My Projects, Templates, Recent Builds, Help/About.
- Project Planner: app idea, target users, category, feature selection.
- Blueprint: screens, workflows, data model, supported/unsupported items.
- Template Gallery: Shop & Inventory, School Records, Expense Tracker, Booking & Appointments, Task Manager, Customer Manager.
- Code Studio: generated files, copy/export, validation results.
- Preview: interactive prototype of the selected supported template.
- Build Center: GitHub repository, build progress, build logs summary, APK availability and checksum.
- Projects: reopen, duplicate, edit, archive/delete with confirmation.

## Architecture
- main.py: Kivy UI, navigation, project persistence, user actions.
- generator_engine.py: deterministic blueprint parsing and template-based source generation.
- templates/: isolated, testable application templates.
- project_schema.py: versioned project manifest and validation.
- build_manager.py: GitHub workflow preparation, dispatch, and build status handling.
- .github/workflows/: build the generated Android app and publish a clearly named APK asset.
- Generated project: main.py, buildozer.spec, requirements.txt, project manifest, README, and workflow.

## Phased implementation
### Phase 0 — Baseline and safety
- Keep the existing app and Generator Engine V2 available.
- Record the current package ID and release workflow.
- Keep V3 work separate from existing user project data.

### Phase 1 — Product foundation
- Add a versioned project schema and validation.
- Add a dashboard and category/template selection.
- Add a transparent feature-support matrix so unsupported requests are not silently represented as working features.

### Phase 2 — Reliable templates
- Implement and test one template at a time, beginning with Shop & Inventory.
- Add School Records, Expense Tracker, Booking & Appointments, Task Manager, and Customer Manager only after each has working data flows and validation.

### Phase 3 — Preview and Code Studio
- Add a template-aware preview and generated-file inspection.
- Add export of the full source project with clear build instructions.

### Phase 4 — Build Center
- Track GitHub Actions run IDs and status.
- Publish APK assets to Releases.
- Show a download link only after verifying a successful run and release asset.
- Record SHA-256 for the exact APK asset.

### Phase 5 — Quality and release
- Test generated app flows and Android installation.
- Test on Android 8.1 and a newer Android version where possible.
- Keep a distinct package ID for test builds until upgrade signing is configured.
- Publish a versioned V3 release and migration notes.

## Definition of done for V3
A user can create a supported app, inspect its blueprint, generate a functioning app with persistent data, preview the supported workflows, build an APK through GitHub Actions, and download the APK from a verified release. The app must report build failures honestly and preserve saved projects during upgrades.

## Current known baseline
- The installed IDEA2APK app is a Kivy Android application.
- Generator Engine V2 currently generates a SQLite-backed Shop & Inventory starter app.
- The existing planner UI is retained until the V3 dashboard and flows are implemented.
- Build #6 uses package ID com.nexgen.idea2apkbuild6 so it can be installed alongside the older package.
