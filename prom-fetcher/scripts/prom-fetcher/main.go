package main

import (
	"encoding/json"
	"fmt"
	"io"
	"net/http"
	"net/url"
	"os"
	"path/filepath"
	"time"

	"github.com/spf13/cobra"
	"github.com/spf13/viper"
	"gopkg.in/yaml.v3"
)

const (
	configDir  = ".config/prom-fetcher"
	configFile = "config.yaml"
	tokenFile  = ".prom-fetcher-token"
)

type Config struct {
	KeycloakURL   string `mapstructure:"keycloak_url"`
	KeycloakRealm string `mapstructure:"keycloak_realm"`
	ClientID      string `mapstructure:"client_id"`
	PrometheusURL string `mapstructure:"prometheus_url"`
}

type TokenResponse struct {
	AccessToken string `json:"access_token"`
	ExpiresIn   int    `json:"expires_in"`
	TokenType   string `json:"token_type"`
}

type TokenCache struct {
	AccessToken string    `json:"access_token"`
	ExpiresAt   time.Time `json:"expires_at"`
}

var (
	cfgFile string
	rootCmd = &cobra.Command{
		Use:   "prom-fetcher",
		Short: "CLI to query Prometheus through Keycloak-authenticated oauth2-proxy",
	}
)

func init() {
	cobra.OnInitialize(initConfig)
	rootCmd.PersistentFlags().StringVar(&cfgFile, "config", "", "config file (default is $HOME/.config/prom-fetcher/config.yaml)")

	rootCmd.AddCommand(queryCmd())
	rootCmd.AddCommand(alertsCmd())
	rootCmd.AddCommand(configCmd())
}

func initConfig() {
	if cfgFile != "" {
		viper.SetConfigFile(cfgFile)
	} else {
		home, err := os.UserHomeDir()
		cobra.CheckErr(err)

		configPath := filepath.Join(home, configDir)
		os.MkdirAll(configPath, 0700)

		viper.AddConfigPath(configPath)
		viper.SetConfigName("config")
		viper.SetConfigType("yaml")
	}

	viper.SetEnvPrefix("PROM_FETCHER")
	viper.AutomaticEnv()

	viper.SetDefault("keycloak_url", "https://auth.doesthings.io")
	viper.SetDefault("keycloak_realm", "doesthings.io")
	viper.SetDefault("client_id", "prom-fetcher")
	viper.SetDefault("prometheus_url", "https://prometheus.doesthings.io")

	if err := viper.ReadInConfig(); err != nil {
		if _, ok := err.(viper.ConfigFileNotFoundError); !ok {
			fmt.Fprintf(os.Stderr, "Error reading config: %v\n", err)
		}
	}
}

func getTokenCachePath() string {
	home, _ := os.UserHomeDir()
	return filepath.Join(home, tokenFile)
}

func loadCachedToken() (*TokenCache, error) {
	path := getTokenCachePath()
	data, err := os.ReadFile(path)
	if err != nil {
		return nil, err
	}

	var cache TokenCache
	if err := json.Unmarshal(data, &cache); err != nil {
		return nil, err
	}

	// Check if token is expired (with 60 second buffer)
	if time.Now().Add(60 * time.Second).After(cache.ExpiresAt) {
		return nil, fmt.Errorf("token expired")
	}

	return &cache, nil
}

func saveCachedToken(cache *TokenCache) error {
	path := getTokenCachePath()
	data, err := json.Marshal(cache)
	if err != nil {
		return err
	}

	// Write with 0600 permissions (owner read/write only)
	return os.WriteFile(path, data, 0600)
}

func fetchNewToken() (string, error) {
	clientSecret := viper.GetString("client_secret")
	if clientSecret == "" {
		return "", fmt.Errorf("PROM_FETCHER_CLIENT_SECRET environment variable not set")
	}

	keycloakURL := viper.GetString("keycloak_url")
	realm := viper.GetString("keycloak_realm")
	clientID := viper.GetString("client_id")

	tokenURL := fmt.Sprintf("%s/realms/%s/protocol/openid-connect/token", keycloakURL, realm)

	data := url.Values{}
	data.Set("grant_type", "client_credentials")
	data.Set("client_id", clientID)
	data.Set("client_secret", clientSecret)

	resp, err := http.PostForm(tokenURL, data)
	if err != nil {
		return "", fmt.Errorf("failed to request token: %w", err)
	}
	defer resp.Body.Close()

	if resp.StatusCode != http.StatusOK {
		body, _ := io.ReadAll(resp.Body)
		return "", fmt.Errorf("token request failed: %s - %s", resp.Status, string(body))
	}

	var tokenResp TokenResponse
	if err := json.NewDecoder(resp.Body).Decode(&tokenResp); err != nil {
		return "", fmt.Errorf("failed to decode token response: %w", err)
	}

	// Cache the token
	cache := TokenCache{
		AccessToken: tokenResp.AccessToken,
		ExpiresAt:   time.Now().Add(time.Duration(tokenResp.ExpiresIn) * time.Second),
	}
	if err := saveCachedToken(&cache); err != nil {
		fmt.Fprintf(os.Stderr, "Warning: failed to cache token: %v\n", err)
	}

	return tokenResp.AccessToken, nil
}

func getAccessToken() (string, error) {
	// Try cached token first
	cache, err := loadCachedToken()
	if err == nil {
		return cache.AccessToken, nil
	}

	// Fetch new token
	return fetchNewToken()
}

func queryPrometheus(endpoint string, queryParams url.Values) (map[string]interface{}, error) {
	token, err := getAccessToken()
	if err != nil {
		return nil, err
	}

	promURL := viper.GetString("prometheus_url")
	fullURL := fmt.Sprintf("%s%s?%s", promURL, endpoint, queryParams.Encode())

	req, err := http.NewRequest("GET", fullURL, nil)
	if err != nil {
		return nil, err
	}

	req.Header.Set("Authorization", "Bearer "+token)

	client := &http.Client{Timeout: 30 * time.Second}
	resp, err := client.Do(req)
	if err != nil {
		return nil, fmt.Errorf("request failed: %w", err)
	}
	defer resp.Body.Close()

	if resp.StatusCode != http.StatusOK {
		body, _ := io.ReadAll(resp.Body)
		return nil, fmt.Errorf("prometheus returned %s: %s", resp.Status, string(body))
	}

	var result map[string]interface{}
	if err := json.NewDecoder(resp.Body).Decode(&result); err != nil {
		return nil, fmt.Errorf("failed to decode response: %w", err)
	}

	return result, nil
}

func queryCmd() *cobra.Command {
	return &cobra.Command{
		Use:   "query <promql>",
		Short: "Execute a PromQL query",
		Args:  cobra.ExactArgs(1),
		RunE: func(cmd *cobra.Command, args []string) error {
			query := args[0]
			params := url.Values{}
			params.Set("query", query)

			result, err := queryPrometheus("/api/v1/query", params)
			if err != nil {
				return err
			}

			output, err := json.MarshalIndent(result, "", "  ")
			if err != nil {
				return err
			}

			fmt.Println(string(output))
			return nil
		},
	}
}

func alertsCmd() *cobra.Command {
	var state string

	cmd := &cobra.Command{
		Use:   "alerts",
		Short: "List firing Prometheus alerts",
		RunE: func(cmd *cobra.Command, args []string) error {
			query := "ALERTS{alertstate=\"firing\"}"
			if state != "" {
				query = fmt.Sprintf("ALERTS{alertstate=\"%s\"}", state)
			}

			params := url.Values{}
			params.Set("query", query)

			result, err := queryPrometheus("/api/v1/query", params)
			if err != nil {
				return err
			}

			output, err := json.MarshalIndent(result, "", "  ")
			if err != nil {
				return err
			}

			fmt.Println(string(output))
			return nil
		},
	}

	cmd.Flags().StringVar(&state, "state", "firing", "Alert state to filter (firing, pending)")
	return cmd
}

func configCmd() *cobra.Command {
	return &cobra.Command{
		Use:   "config",
		Short: "Show current configuration",
		Run: func(cmd *cobra.Command, args []string) {
			config := Config{
				KeycloakURL:   viper.GetString("keycloak_url"),
				KeycloakRealm: viper.GetString("keycloak_realm"),
				ClientID:      viper.GetString("client_id"),
				PrometheusURL: viper.GetString("prometheus_url"),
			}

			// Don't print the secret
			output, _ := yaml.Marshal(config)
			fmt.Println("Configuration:")
			fmt.Println(string(output))

			if viper.GetString("client_secret") != "" {
				fmt.Println("Client secret: set via PROM_FETCHER_CLIENT_SECRET")
			} else {
				fmt.Println("Client secret: NOT SET (set PROM_FETCHER_CLIENT_SECRET)")
			}
		},
	}
}

func main() {
	if err := rootCmd.Execute(); err != nil {
		fmt.Fprintf(os.Stderr, "Error: %v\n", err)
		os.Exit(1)
	}
}
