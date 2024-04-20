package:
	#docker pull registry.dp.tech/mlops/mesh-viewer:latest
	docker buildx build --network=host --platform linux/amd64 -f Dockerfile -t app-particle --cache-from registry.dp.tech/mlops/mesh-viewer:latest .
	docker tag app-particle registry.dp.tech/mlops/mesh-viewer:latest
	docker push registry.dp.tech/mlops/mesh-viewer:latest

deploy:
	kubectl --kubeconfig ~/.kube/mlops_zjk apply -f k8s-manifest/ -n project-launching
	kubectl --kubeconfig ~/.kube/mlops_zjk rollout restart deploy -n  -n project-launching
